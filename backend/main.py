from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
from datetime import datetime, timedelta
import os
import logging

from models import (
    User, Transaction, TransactionCategory, Achievement, UserAchievement,
    Module, Lesson, LessonProgress, Stock, UserStock, MarketEvent,
    UserMarketEventAction, DailyMission, UserDailyMission, AdaptiveMastery,
    AdaptiveQuestion, get_db, init_db
)
from llm_agent import parse_transaction_with_llm, evaluate_purchase_with_llm, generate_lesson_with_llm, generate_adaptive_question_with_llm

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Financial AI Assistant")

# CORS из переменных окружения
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Временно разрешаем все origins для отладки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class ChatRequest(BaseModel):
    user_id: int
    message: str

class ChatResponse(BaseModel):
    success: bool
    message: str
    transaction: dict = None

class TransactionResponse(BaseModel):
    id: int
    amount: float
    category: str
    timestamp: datetime

class DashboardResponse(BaseModel):
    user_id: int
    username: str
    current_balance: float
    financial_score: int
    recent_transactions: List[TransactionResponse]

class PurchaseEvaluationRequest(BaseModel):
    user_id: int
    wish: str

class PurchaseEvaluationResponse(BaseModel):
    necessity_score: int
    verdict: str
    reasoning: str
    current_balance: float

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AddTransactionRequest(BaseModel):
    userId: str
    amount: float
    category: str
    type: str = "expense"  # "income" or "expense"
    description: Optional[str] = None

class CompleteLessonRequest(BaseModel):
    userId: str
    lessonId: int
    correctAnswers: int = 0
    totalQuestions: int = 0

class OnboardingSubmitRequest(BaseModel):
    userId: str
    answers: dict

# ============ Stocks & Trading Schemas ============

class TradeRequest(BaseModel):
    userId: str
    ticker: str
    shares: int
    action: str  # buy or sell

class StockResponse(BaseModel):
    ticker: str
    name: str
    price: float
    change: float
    sector: Optional[str] = None

class PortfolioResponse(BaseModel):
    cash: float
    stocks: List[dict]
    total_value: float

# ============ Market Events Schemas ============

class MarketEventActionRequest(BaseModel):
    userId: str
    eventId: int
    action: str

class MarketEventResponse(BaseModel):
    id: int
    title: str
    description: str
    event_type: str
    impact: str
    options: List[dict]
    expires_at: str

# ============ Daily Missions Schemas ============

class DailyMissionResponse(BaseModel):
    id: int
    title: str
    description: str
    progress: int
    target: int
    xp_reward: int
    completed: bool

# ============ Adaptive Learning Schemas ============

class GenerateLessonRequest(BaseModel):
    userId: str
    weakTopic: Optional[str] = None
    strongTopic: Optional[str] = None

class GeneratedLessonResponse(BaseModel):
    title: str
    content: str
    questions: List[dict]
    xp_reward: int

class AdaptiveAnswerRequest(BaseModel):
    userId: str
    topic: str
    questionId: int
    isCorrect: bool
    timeMs: int = 0
    source: str = "lesson"

class BuyFreezeRequest(BaseModel):
    userId: str

@app.on_event("startup")
async def startup():
    await init_db()

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Получаем пользователя
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Парсим транзакцию через LLM
    try:
        parsed = await parse_transaction_with_llm(request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    amount = float(parsed.get("amount", 0))
    category = parsed.get("category", "other")

    if amount <= 0:
        return ChatResponse(
            success=False,
            message="Не удалось определить сумму транзакции"
        )

    # Создаем транзакцию
    transaction = Transaction(
        user_id=user.id,
        amount=amount,
        category=TransactionCategory[category]
    )
    db.add(transaction)

    # Обновляем баланс
    user.current_balance -= amount

    # Обновляем скоринг (простая логика)
    if user.current_balance < 0:
        user.financial_score = max(0, user.financial_score - 50)
    else:
        user.financial_score = min(1000, user.financial_score + 10)

    await db.commit()
    await db.refresh(transaction)

    return ChatResponse(
        success=True,
        message=f"Транзакция записана: -{amount} руб. в категории {category}. Баланс: {user.current_balance:.2f} руб.",
        transaction={
            "id": transaction.id,
            "amount": transaction.amount,
            "category": transaction.category.value,
            "timestamp": transaction.timestamp.isoformat()
        }
    )

@app.get("/api/user/{user_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(user_id: int, db: AsyncSession = Depends(get_db)):
    # Получаем пользователя
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем последние 10 транзакций
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(desc(Transaction.timestamp))
        .limit(10)
    )
    transactions = result.scalars().all()

    return DashboardResponse(
        user_id=user.id,
        username=user.username,
        current_balance=user.current_balance,
        financial_score=user.financial_score,
        recent_transactions=[
            TransactionResponse(
                id=t.id,
                amount=t.amount,
                category=t.category.value,
                timestamp=t.timestamp
            )
            for t in transactions
        ]
    )

@app.post("/api/user/create")
async def create_user(username: str, initial_balance: float = 10000.0, db: AsyncSession = Depends(get_db)):
    # Проверяем, существует ли пользователь
    result = await db.execute(select(User).where(User.username == username))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return {
            "user_id": existing_user.id,
            "username": existing_user.username,
            "balance": existing_user.current_balance,
            "message": "User already exists"
        }

    user = User(username=username, current_balance=initial_balance)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "user_id": user.id,
        "username": user.username,
        "balance": user.current_balance,
        "message": "User created successfully"
    }

@app.get("/api/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "balance": u.current_balance,
                "score": u.financial_score
            }
            for u in users
        ]
    }

@app.get("/")
async def root():
    return {"message": "Financial AI Assistant API", "status": "running"}

@app.post("/api/evaluate-purchase", response_model=PurchaseEvaluationResponse)
async def evaluate_purchase(request: PurchaseEvaluationRequest, db: AsyncSession = Depends(get_db)):
    # Получаем пользователя
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Оцениваем покупку через LLM
    evaluation = await evaluate_purchase_with_llm(request.wish, user.current_balance)

    return PurchaseEvaluationResponse(
        necessity_score=evaluation.get("necessity_score", 5),
        verdict=evaluation.get("verdict", "Подумай еще раз"),
        reasoning=evaluation.get("reasoning", "Нужно больше данных для оценки"),
        current_balance=user.current_balance
    )

# ============ Эндпоинты для фронтенда ============

@app.get("/api/dashboard")
async def get_dashboard_frontend(userId: str, db: AsyncSession = Depends(get_db)):
    """Дашборд для фронтенда с полной статистикой"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем все транзакции за последние 30 дней
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .where(Transaction.timestamp >= thirty_days_ago)
        .order_by(desc(Transaction.timestamp))
    )
    all_transactions = result.scalars().all()

    # Последние 10 для отображения
    recent_transactions = all_transactions[:10]

    # Считаем расходы за месяц
    total_expenses = sum(t.amount for t in all_transactions)

    # Прогноз: сколько дней хватит денег
    if total_expenses > 0:
        daily_avg = total_expenses / 30
        days_left = int(user.current_balance / daily_avg) if daily_avg > 0 else 999
    else:
        daily_avg = 0
        days_left = 999

    # Статистика по категориям
    spending_by_category = {}
    for t in all_transactions:
        cat = t.category.value
        spending_by_category[cat] = spending_by_category.get(cat, 0) + t.amount

    # AI советы на основе трат
    ai_tips = []
    if user.current_balance < 1000:
        ai_tips.append("⚠️ Баланс критически низкий! Сократите расходы.")
    elif total_expenses > user.current_balance * 0.5:
        ai_tips.append("💡 Вы тратите больше половины баланса в месяц. Будьте осторожнее!")
    else:
        ai_tips.append("✅ Отличная работа! Ваши траты под контролем.")

    ai_tips.append(f"📊 Финансовый скоринг: {user.financial_score}/1000")

    if spending_by_category.get("food", 0) > total_expenses * 0.4:
        ai_tips.append("🍔 Расходы на еду составляют более 40%. Попробуйте готовить дома!")

    return {
        "balance": user.current_balance,
        "income": 0,
        "expenses": total_expenses,
        "transactions": [
            {
                "id": t.id,
                "amount": abs(t.amount),
                "type": t.transaction_type if hasattr(t, 'transaction_type') else "expense",
                "category": t.category.value,
                "timestamp": t.timestamp.isoformat() if t.timestamp else datetime.utcnow().isoformat(),
                "description": t.description or f"Покупка в категории {t.category.value}"
            }
            for t in recent_transactions
        ],
        "forecast": {
            "days_left": days_left,
            "daily_avg": daily_avg,
            "message": f"При текущих тратах денег хватит на {days_left} дней" if days_left < 999 else "Отличный баланс!"
        },
        "ai_tips": ai_tips,
        "spending_chart": [
            {"category": cat, "amount": amount}
            for cat, amount in spending_by_category.items()
        ],
        "stats": {
            "level": user.level,
            "xp": user.xp,
            "streak": user.streak
        }
    }

@app.get("/api/transactions")
async def get_transactions_frontend(userId: str, limit: int = 30, db: AsyncSession = Depends(get_db)):
    """Список транзакций для фронтенда"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.timestamp))
        .limit(limit)
    )
    transactions = result.scalars().all()

    return [
        {
            "id": t.id,
            "amount": abs(t.amount),
            "type": t.transaction_type if hasattr(t, 'transaction_type') else "expense",
            "category": t.category.value,
            "timestamp": t.timestamp.isoformat() if t.timestamp else datetime.utcnow().isoformat(),
            "description": t.description or f"Покупка в категории {t.category.value}"
        }
        for t in transactions
    ]

@app.post("/api/transactions")
async def add_transaction_frontend(request: AddTransactionRequest, db: AsyncSession = Depends(get_db)):
    """Добавить транзакцию"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Создаем транзакцию
    try:
        cat = TransactionCategory[request.category]
    except KeyError:
        cat = TransactionCategory.other

    from datetime import datetime

    transaction = Transaction(
        user_id=user.id,
        amount=abs(request.amount),
        category=cat,
        transaction_type=request.type,
        description=request.description,
        timestamp=datetime.utcnow()
    )
    db.add(transaction)

    # Обновляем баланс и XP
    if request.type == "income":
        user.current_balance += abs(request.amount)
    else:  # expense
        user.current_balance -= abs(request.amount)

    user.xp += 5
    user.last_activity = datetime.utcnow()

    # Проверка уровня
    if user.xp >= 100:
        user.level += 1
        user.xp = 0

    await db.commit()
    await db.refresh(transaction)

    return {
        "id": transaction.id,
        "amount": -transaction.amount,
        "category": transaction.category.value,
        "timestamp": transaction.timestamp.isoformat(),
        "description": transaction.description
    }

@app.delete("/api/transactions/{transactionId}")
async def delete_transaction_frontend(transactionId: int, userId: str, db: AsyncSession = Depends(get_db)):
    """Удалить транзакцию"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transactionId)
        .where(Transaction.user_id == user.id)
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Возвращаем деньги
    user.current_balance += transaction.amount

    await db.delete(transaction)
    await db.commit()

    return {"status": "deleted"}

@app.post("/api/register")
async def register_frontend(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Регистрация пользователя"""
    # Проверяем, существует ли пользователь
    result = await db.execute(select(User).where(User.email == request.email))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Создаем пользователя
    user = User(
        username=request.email,
        email=request.email,
        name=request.name,
        current_balance=10000.0,
        financial_score=500,
        level=1,
        xp=0,
        streak=0
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "access_token": f"user_{user.id}",
        "name": request.name,
        "email": request.email,
        "is_admin": request.email == "admin@admin.com"
    }

@app.post("/api/login")
async def login_frontend(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Вход пользователя"""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        # Если пользователь не найден по email, пробуем по username
        result = await db.execute(select(User).where(User.username == request.email))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "access_token": f"user_{user.id}",
        "name": user.name or user.username,
        "email": user.email or user.username,
        "is_admin": (user.email == "admin@admin.com" or user.username == "admin@admin.com")
    }

# ============ Достижения ============

@app.get("/api/achievements")
async def get_achievements(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить достижения пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем все достижения пользователя
    result = await db.execute(
        select(UserAchievement, Achievement)
        .join(Achievement)
        .where(UserAchievement.user_id == user.id)
    )
    user_achievements = result.all()

    # Получаем все доступные достижения
    result = await db.execute(select(Achievement))
    all_achievements = result.scalars().all()

    unlocked_ids = {ua.achievement_id for ua, _ in user_achievements}

    achievements_list = []
    for achievement in all_achievements:
        is_unlocked = achievement.id in unlocked_ids
        user_ach = next((ua for ua, a in user_achievements if a.id == achievement.id), None)

        achievements_list.append({
            "id": achievement.id,
            "name": achievement.name if hasattr(achievement, 'name') else achievement.title,
            "title": achievement.title,
            "description": achievement.description,
            "icon": achievement.icon,
            "category": achievement.category if hasattr(achievement, 'category') else "other",
            "xp_reward": achievement.xp_reward,
            "unlocked": is_unlocked,
            "progress": user_ach.progress if user_ach else 0,
            "unlocked_at": user_ach.unlocked_at.isoformat() if user_ach and is_unlocked else None
        })

    return {
        "achievements": achievements_list,
        "daily_missions": []  # Можно добавить ежедневные миссии позже
    }

# ============ Обучение (Модули и Уроки) ============

@app.get("/api/v2/modules")
async def get_modules(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить все модули обучения"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем все модули
    result = await db.execute(select(Module).order_by(Module.order))
    modules = result.scalars().all()

    modules_list = []
    for module in modules:
        # Считаем прогресс по урокам модуля
        result = await db.execute(
            select(func.count(LessonProgress.id))
            .join(Lesson)
            .where(Lesson.module_id == module.id)
            .where(LessonProgress.user_id == user.id)
            .where(LessonProgress.completed == True)
        )
        completed_lessons = result.scalar() or 0

        result = await db.execute(
            select(func.count(Lesson.id))
            .where(Lesson.module_id == module.id)
        )
        total_lessons = result.scalar() or 0

        modules_list.append({
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "icon": module.icon,
            "progress": completed_lessons,
            "total": total_lessons,
            "locked": user.level < module.required_level
        })

    return modules_list

@app.get("/api/v2/lessons")
async def get_module_lessons(userId: str, moduleId: int, db: AsyncSession = Depends(get_db)):
    """Получить уроки модуля"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем уроки модуля
    result = await db.execute(
        select(Lesson)
        .where(Lesson.module_id == moduleId)
        .order_by(Lesson.order)
    )
    lessons = result.scalars().all()

    lessons_list = []
    for lesson in lessons:
        # Проверяем прогресс
        result = await db.execute(
            select(LessonProgress)
            .where(LessonProgress.user_id == user.id)
            .where(LessonProgress.lesson_id == lesson.id)
        )
        progress = result.scalar_one_or_none()

        lessons_list.append({
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "xp_reward": lesson.xp_reward,
            "completed": progress.completed if progress else False,
            "score": progress.score if progress else 0,
            "locked": user.level < lesson.required_level
        })

    return lessons_list

@app.get("/api/v2/lesson/{lessonId}")
async def get_lesson_detail(lessonId: int, userId: str, db: AsyncSession = Depends(get_db)):
    """Получить детали урока"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Lesson).where(Lesson.id == lessonId))
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return {
        "id": lesson.id,
        "title": lesson.title,
        "description": lesson.description,
        "content": lesson.content,
        "questions": lesson.questions or [],
        "xp_reward": lesson.xp_reward
    }

@app.post("/api/v2/complete-lesson")
async def complete_lesson(request: CompleteLessonRequest, db: AsyncSession = Depends(get_db)):
    """Завершить урок"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Lesson).where(Lesson.id == request.lessonId))
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Проверяем существующий прогресс
    result = await db.execute(
        select(LessonProgress)
        .where(LessonProgress.user_id == user.id)
        .where(LessonProgress.lesson_id == request.lessonId)
    )
    progress = result.scalar_one_or_none()

    score = int((request.correctAnswers / request.totalQuestions * 100)) if request.totalQuestions > 0 else 100

    if progress:
        progress.completed = True
        progress.score = max(progress.score, score)
        progress.completed_at = datetime.utcnow()
    else:
        progress = LessonProgress(
            user_id=user.id,
            lesson_id=request.lessonId,
            completed=True,
            score=score,
            completed_at=datetime.utcnow()
        )
        db.add(progress)

    # Начисляем XP
    user.xp += lesson.xp_reward
    user.last_activity = datetime.utcnow()

    # Проверка уровня
    while user.xp >= 100:
        user.level += 1
        user.xp -= 100

    await db.commit()

    return {
        "success": True,
        "xp_earned": lesson.xp_reward,
        "new_level": user.level,
        "new_xp": user.xp
    }

# ============ Onboarding ============

@app.get("/api/onboarding/status")
async def get_onboarding_status(userId: str, db: AsyncSession = Depends(get_db)):
    """Проверить статус онбординга"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        return {"completed": False}

    return {"completed": user.onboarding_completed}

@app.get("/api/onboarding/questions")
async def get_onboarding_questions():
    """Получить вопросы онбординга"""
    return [
        {
            "id": 1,
            "question": "Какой у вас опыт управления финансами?",
            "options": ["Новичок", "Средний", "Продвинутый"]
        },
        {
            "id": 2,
            "question": "Какая ваша основная финансовая цель?",
            "options": ["Накопить деньги", "Контролировать расходы", "Инвестировать", "Научиться финансовой грамотности"]
        },
        {
            "id": 3,
            "question": "Как часто вы отслеживаете свои расходы?",
            "options": ["Каждый день", "Раз в неделю", "Раз в месяц", "Никогда"]
        }
    ]

@app.post("/api/onboarding/submit")
async def submit_onboarding(request: OnboardingSubmitRequest, db: AsyncSession = Depends(get_db)):
    """Сохранить ответы онбординга"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.onboarding_completed = True
    user.onboarding_data = request.answers

    await db.commit()

    return {"success": True}

@app.get("/api/onboarding/result")
async def get_onboarding_result(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить результаты онбординга"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "profile": "Начинающий инвестор",
        "recommendations": [
            "Начните с отслеживания ежедневных расходов",
            "Установите финансовую цель на месяц",
            "Изучите базовые уроки по финансовой грамотности"
        ]
    }

# ============ Portfolio ============

@app.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Портфолио пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем акции пользователя
    result = await db.execute(
        select(UserStock, Stock)
        .join(Stock)
        .where(UserStock.user_id == user.id)
        .where(UserStock.shares > 0)
    )
    user_stocks = result.all()

    stocks_list = []
    total_stocks_value = 0.0

    for user_stock, stock in user_stocks:
        current_value = stock.current_price * user_stock.shares
        profit = (stock.current_price - user_stock.avg_buy_price) * user_stock.shares
        profit_percent = ((stock.current_price - user_stock.avg_buy_price) / user_stock.avg_buy_price * 100) if user_stock.avg_buy_price > 0 else 0

        stocks_list.append({
            "ticker": stock.ticker,
            "name": stock.name,
            "shares": user_stock.shares,
            "avg_price": user_stock.avg_buy_price,
            "current_price": stock.current_price,
            "value": current_value,
            "profit": profit,
            "profit_percent": profit_percent
        })
        total_stocks_value += current_value

    total_value = user.current_balance + total_stocks_value

    return PortfolioResponse(
        cash=user.current_balance,
        stocks=stocks_list,
        total_value=total_value
    )

@app.post("/api/check-portfolio")
async def check_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Проверить портфолио"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "ok", "user_id": user.id}

# ============ Progress ============

@app.get("/api/progress")
async def get_progress(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить прогресс пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Считаем завершенные уроки
    result = await db.execute(
        select(func.count(LessonProgress.id))
        .where(LessonProgress.user_id == user.id)
        .where(LessonProgress.completed == True)
    )
    completed_lessons = result.scalar() or 0

    # Считаем транзакции
    result = await db.execute(
        select(func.count(Transaction.id))
        .where(Transaction.user_id == user.id)
    )
    total_transactions = result.scalar() or 0

    return {
        "level": user.level,
        "xp": user.xp,
        "xp_to_next_level": 100,
        "streak": user.streak,
        "completed_lessons": completed_lessons,
        "total_transactions": total_transactions,
        "financial_score": user.financial_score
    }

# ============ Diary ============

@app.get("/api/diary")
async def get_diary(userId: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Получить дневник активности"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем последние транзакции как активность
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.timestamp))
        .limit(limit)
    )
    transactions = result.scalars().all()

    diary_entries = []
    for t in transactions:
        diary_entries.append({
            "id": t.id,
            "type": "transaction",
            "message": f"Потрачено {t.amount} руб. на {t.category.value}",
            "timestamp": t.timestamp.isoformat(),
            "icon": "💰"
        })

    return diary_entries

# ============ Levels ============

@app.get("/api/levels")
async def get_levels():
    """Получить информацию об уровнях"""
    return [
        {"level": i, "xp_required": 100, "title": f"Уровень {i}"}
        for i in range(1, 51)
    ]

# ============ Заглушки для неиспользуемых функций ============

@app.get("/api/daily-missions")
async def get_daily_missions(userId: str, db: AsyncSession = Depends(get_db)):
    """Ежедневные миссии"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем миссии на сегодня
    today = datetime.utcnow().date()
    result = await db.execute(
        select(DailyMission)
        .where(func.date(DailyMission.date) == today)
    )
    daily_missions = result.scalars().all()

    # Если миссий нет, создаем их
    if not daily_missions:
        missions_data = [
            {
                "title": "Добавьте 3 транзакции",
                "description": "Отследите свои расходы",
                "mission_type": "transaction",
                "target_value": 3,
                "xp_reward": 50
            },
            {
                "title": "Пройдите 1 урок",
                "description": "Изучите финансовую грамотность",
                "mission_type": "lesson",
                "target_value": 1,
                "xp_reward": 100
            },
            {
                "title": "Войдите в систему",
                "description": "Поддерживайте серию",
                "mission_type": "login",
                "target_value": 1,
                "xp_reward": 20
            }
        ]

        for mission_data in missions_data:
            mission = DailyMission(**mission_data, date=datetime.utcnow())
            db.add(mission)

        await db.commit()

        # Перезагружаем миссии
        result = await db.execute(
            select(DailyMission)
            .where(func.date(DailyMission.date) == today)
        )
        daily_missions = result.scalars().all()

    # Получаем прогресс пользователя по миссиям
    missions_list = []
    for mission in daily_missions:
        result = await db.execute(
            select(UserDailyMission)
            .where(UserDailyMission.user_id == user.id)
            .where(UserDailyMission.mission_id == mission.id)
        )
        user_mission = result.scalar_one_or_none()

        # Если прогресса нет, создаем
        if not user_mission:
            user_mission = UserDailyMission(
                user_id=user.id,
                mission_id=mission.id,
                progress=0,
                completed=False
            )
            db.add(user_mission)

        # Вычисляем текущий прогресс
        current_progress = 0
        if mission.mission_type == "transaction":
            # Считаем транзакции за сегодня
            result = await db.execute(
                select(func.count(Transaction.id))
                .where(Transaction.user_id == user.id)
                .where(func.date(Transaction.timestamp) == today)
            )
            current_progress = result.scalar() or 0

        elif mission.mission_type == "lesson":
            # Считаем уроки за сегодня
            result = await db.execute(
                select(func.count(LessonProgress.id))
                .where(LessonProgress.user_id == user.id)
                .where(func.date(LessonProgress.completed_at) == today)
                .where(LessonProgress.completed == True)
            )
            current_progress = result.scalar() or 0

        elif mission.mission_type == "login":
            # Проверяем, заходил ли сегодня
            if user.last_activity and user.last_activity.date() == today:
                current_progress = 1

        # Обновляем прогресс
        user_mission.progress = current_progress
        if current_progress >= mission.target_value and not user_mission.completed:
            user_mission.completed = True
            user_mission.completed_at = datetime.utcnow()
            # Начисляем XP
            user.xp += mission.xp_reward

        missions_list.append({
            "id": mission.id,
            "title": mission.title,
            "description": mission.description,
            "progress": current_progress,
            "target": mission.target_value,
            "xp_reward": mission.xp_reward,
            "completed": user_mission.completed
        })

    await db.commit()

    return missions_list

@app.post("/api/buy-freeze")
async def buy_freeze(request: BuyFreezeRequest, db: AsyncSession = Depends(get_db)):
    """Покупка заморозки"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    freeze_cost = 500.0  # Стоимость заморозки

    if user.current_balance < freeze_cost:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    # Списываем деньги
    user.current_balance -= freeze_cost

    # Увеличиваем streak на 1 день (заморозка)
    user.streak += 1

    await db.commit()

    logger.info(f"User {user.username} bought freeze for {freeze_cost}")

    return {
        "success": True,
        "message": "Заморозка куплена! Ваша серия сохранена.",
        "new_balance": user.current_balance,
        "new_streak": user.streak
    }

@app.get("/api/stocks")
async def get_stocks(userId: str, db: AsyncSession = Depends(get_db)):
    """Список акций"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем все доступные акции
    result = await db.execute(select(Stock))
    stocks = result.scalars().all()

    stocks_list = []
    for stock in stocks:
        stocks_list.append({
            "ticker": stock.ticker,
            "name": stock.name,
            "price": stock.current_price,
            "change": stock.change_percent,
            "sector": stock.sector
        })

    return stocks_list

@app.get("/api/stock/{ticker}")
async def get_stock_detail(ticker: str, userId: str, db: AsyncSession = Depends(get_db)):
    """Детали акции"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Проверяем, есть ли у пользователя эта акция
    result = await db.execute(
        select(UserStock)
        .where(UserStock.user_id == user.id)
        .where(UserStock.stock_id == stock.id)
    )
    user_stock = result.scalar_one_or_none()

    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "price": stock.current_price,
        "change": stock.change_percent,
        "sector": stock.sector,
        "description": stock.description,
        "user_shares": user_stock.shares if user_stock else 0,
        "user_avg_price": user_stock.avg_buy_price if user_stock else 0
    }

@app.get("/api/market-event")
async def get_market_event(userId: str, db: AsyncSession = Depends(get_db)):
    """Рыночные события"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем активное событие, которое еще не истекло
    now = datetime.utcnow()
    result = await db.execute(
        select(MarketEvent)
        .where(MarketEvent.active == True)
        .where(MarketEvent.expires_at > now)
        .order_by(desc(MarketEvent.created_at))
        .limit(1)
    )
    event = result.scalar_one_or_none()

    if not event:
        return None

    # Проверяем, не отвечал ли пользователь уже на это событие
    result = await db.execute(
        select(UserMarketEventAction)
        .where(UserMarketEventAction.user_id == user.id)
        .where(UserMarketEventAction.event_id == event.id)
    )
    user_action = result.scalar_one_or_none()

    if user_action:
        # Пользователь уже ответил на это событие
        return None

    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_type": event.event_type,
        "impact": event.impact,
        "ticker": event.ticker,
        "options": event.options,
        "expires_at": event.expires_at.isoformat()
    }

@app.post("/api/market-event/action")
async def market_event_action(request: MarketEventActionRequest, db: AsyncSession = Depends(get_db)):
    """Действие на событие"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(MarketEvent).where(MarketEvent.id == request.eventId))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Проверяем, не истекло ли событие
    if event.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Event expired")

    # Проверяем, не отвечал ли пользователь уже
    result = await db.execute(
        select(UserMarketEventAction)
        .where(UserMarketEventAction.user_id == user.id)
        .where(UserMarketEventAction.event_id == event.id)
    )
    existing_action = result.scalar_one_or_none()

    if existing_action:
        raise HTTPException(status_code=400, detail="Already responded to this event")

    # Обрабатываем действие
    result_data = {}
    xp_earned = 0

    if request.action == "buy":
        # Покупка акций по событию
        if event.ticker:
            result = await db.execute(select(Stock).where(Stock.ticker == event.ticker))
            stock = result.scalar_one_or_none()

            if stock and user.current_balance >= stock.current_price:
                # Покупаем 1 акцию
                user.current_balance -= stock.current_price

                result = await db.execute(
                    select(UserStock)
                    .where(UserStock.user_id == user.id)
                    .where(UserStock.stock_id == stock.id)
                )
                user_stock = result.scalar_one_or_none()

                if user_stock:
                    total_shares = user_stock.shares + 1
                    total_value = (user_stock.avg_buy_price * user_stock.shares) + stock.current_price
                    user_stock.avg_buy_price = total_value / total_shares
                    user_stock.shares = total_shares
                else:
                    user_stock = UserStock(
                        user_id=user.id,
                        stock_id=stock.id,
                        shares=1,
                        avg_buy_price=stock.current_price
                    )
                    db.add(user_stock)

                result_data = {"action": "bought", "ticker": stock.ticker, "shares": 1}
                xp_earned = 50

    elif request.action == "sell":
        # Продажа акций по событию
        if event.ticker:
            result = await db.execute(select(Stock).where(Stock.ticker == event.ticker))
            stock = result.scalar_one_or_none()

            if stock:
                result = await db.execute(
                    select(UserStock)
                    .where(UserStock.user_id == user.id)
                    .where(UserStock.stock_id == stock.id)
                )
                user_stock = result.scalar_one_or_none()

                if user_stock and user_stock.shares > 0:
                    user.current_balance += stock.current_price
                    user_stock.shares -= 1
                    result_data = {"action": "sold", "ticker": stock.ticker, "shares": 1}
                    xp_earned = 50

    elif request.action == "hold":
        # Ничего не делаем
        result_data = {"action": "hold"}
        xp_earned = 20

    # Сохраняем действие пользователя
    user_action = UserMarketEventAction(
        user_id=user.id,
        event_id=event.id,
        action=request.action,
        result=result_data
    )
    db.add(user_action)

    # Начисляем XP
    user.xp += xp_earned
    user.last_activity = datetime.utcnow()

    await db.commit()

    logger.info(f"User {user.username} responded to market event {event.id} with action {request.action}")

    return {
        "success": True,
        "result": result_data,
        "xp_earned": xp_earned
    }

@app.get("/api/recommendations")
async def get_recommendations(userId: str, db: AsyncSession = Depends(get_db)):
    """Рекомендации"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    recommendations = []

    # Рекомендации на основе баланса
    if user.current_balance > 5000:
        recommendations.append({
            "type": "investment",
            "title": "Рассмотрите инвестиции",
            "description": f"У вас {user.current_balance:.0f} руб. Можно начать инвестировать в акции.",
            "action": "stocks"
        })

    # Рекомендации на основе уровня
    if user.level < 5:
        recommendations.append({
            "type": "learning",
            "title": "Пройдите обучение",
            "description": "Изучите основы финансовой грамотности для повышения уровня.",
            "action": "learn"
        })

    # Рекомендации на основе активности
    if user.streak < 3:
        recommendations.append({
            "type": "activity",
            "title": "Поддерживайте активность",
            "description": "Заходите каждый день, чтобы увеличить серию.",
            "action": "daily"
        })

    return recommendations

@app.post("/api/trade")
async def trade(request: TradeRequest, db: AsyncSession = Depends(get_db)):
    """Торговля акциями"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Stock).where(Stock.ticker == request.ticker))
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    if request.action == "buy":
        # Покупка акций
        total_cost = stock.current_price * request.shares

        if user.current_balance < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        # Списываем деньги
        user.current_balance -= total_cost

        # Проверяем, есть ли уже эта акция у пользователя
        result = await db.execute(
            select(UserStock)
            .where(UserStock.user_id == user.id)
            .where(UserStock.stock_id == stock.id)
        )
        user_stock = result.scalar_one_or_none()

        if user_stock:
            # Обновляем среднюю цену покупки
            total_shares = user_stock.shares + request.shares
            total_value = (user_stock.avg_buy_price * user_stock.shares) + (stock.current_price * request.shares)
            user_stock.avg_buy_price = total_value / total_shares
            user_stock.shares = total_shares
        else:
            # Создаем новую запись
            user_stock = UserStock(
                user_id=user.id,
                stock_id=stock.id,
                shares=request.shares,
                avg_buy_price=stock.current_price
            )
            db.add(user_stock)

        # Начисляем XP за инвестирование
        user.xp += 10
        user.last_activity = datetime.utcnow()

        await db.commit()

        logger.info(f"User {user.username} bought {request.shares} shares of {stock.ticker} for {total_cost}")

        return {
            "success": True,
            "message": f"Куплено {request.shares} акций {stock.ticker}",
            "new_balance": user.current_balance,
            "total_cost": total_cost
        }

    elif request.action == "sell":
        # Продажа акций
        result = await db.execute(
            select(UserStock)
            .where(UserStock.user_id == user.id)
            .where(UserStock.stock_id == stock.id)
        )
        user_stock = result.scalar_one_or_none()

        if not user_stock or user_stock.shares < request.shares:
            raise HTTPException(status_code=400, detail="Insufficient shares")

        # Продаем акции
        total_revenue = stock.current_price * request.shares
        user.current_balance += total_revenue
        user_stock.shares -= request.shares

        # Начисляем XP
        user.xp += 10
        user.last_activity = datetime.utcnow()

        await db.commit()

        logger.info(f"User {user.username} sold {request.shares} shares of {stock.ticker} for {total_revenue}")

        return {
            "success": True,
            "message": f"Продано {request.shares} акций {stock.ticker}",
            "new_balance": user.current_balance,
            "total_revenue": total_revenue
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid action")

@app.post("/api/reset-portfolio")
async def reset_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Сброс портфолио"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Удаляем все акции пользователя
    result = await db.execute(
        select(UserStock).where(UserStock.user_id == user.id)
    )
    user_stocks = result.scalars().all()

    for user_stock in user_stocks:
        await db.delete(user_stock)

    # Сбрасываем баланс
    user.current_balance = 10000.0

    await db.commit()

    logger.info(f"Portfolio reset for user {user.username}")

    return {"success": True, "message": "Portfolio reset successfully"}

@app.get("/api/experience")
async def get_experience(userId: str, db: AsyncSession = Depends(get_db)):
    """Опыт пользователя (legacy)"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"xp": user.xp, "level": user.level}

@app.post("/api/interactions")
async def post_interaction(userId: str, cardId: int, answer_index: int, db: AsyncSession = Depends(get_db)):
    """Взаимодействия (legacy)"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Начисляем небольшой XP за взаимодействие
    user.xp += 5
    user.last_activity = datetime.utcnow()

    await db.commit()

    return {"success": True, "xp_earned": 5}

# ============ Adaptive Learning ============

@app.get("/api/adaptive/mastery")
async def get_adaptive_mastery(userId: str, db: AsyncSession = Depends(get_db)):
    """Адаптивное обучение - мастерство"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем все темы с мастерством
    result = await db.execute(
        select(AdaptiveMastery)
        .where(AdaptiveMastery.user_id == user.id)
    )
    masteries = result.scalars().all()

    mastery_dict = {}
    for mastery in masteries:
        mastery_dict[mastery.topic] = {
            "level": mastery.mastery_level,
            "correct": mastery.correct_answers,
            "total": mastery.total_answers,
            "last_practiced": mastery.last_practiced.isoformat()
        }

    return mastery_dict

@app.get("/api/adaptive/recommendation")
async def get_adaptive_recommendation(userId: str, db: AsyncSession = Depends(get_db)):
    """Адаптивные рекомендации"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем самую слабую тему
    result = await db.execute(
        select(AdaptiveMastery)
        .where(AdaptiveMastery.user_id == user.id)
        .order_by(AdaptiveMastery.mastery_level)
        .limit(1)
    )
    weakest = result.scalar_one_or_none()

    if not weakest:
        return None

    return {
        "topic": weakest.topic,
        "mastery_level": weakest.mastery_level,
        "recommendation": f"Рекомендуем изучить тему '{weakest.topic}' - ваш уровень мастерства {weakest.mastery_level:.1%}"
    }

@app.get("/api/adaptive/next-question")
async def get_adaptive_next_question(topic: str, userId: str, db: AsyncSession = Depends(get_db)):
    """Следующий вопрос"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем мастерство по теме
    result = await db.execute(
        select(AdaptiveMastery)
        .where(AdaptiveMastery.user_id == user.id)
        .where(AdaptiveMastery.topic == topic)
    )
    mastery = result.scalar_one_or_none()

    # Определяем сложность вопроса на основе мастерства
    if mastery:
        difficulty = min(0.9, mastery.mastery_level + 0.1)
    else:
        difficulty = 0.3  # Начальная сложность

    # Получаем вопрос из базы или генерируем новый
    result = await db.execute(
        select(AdaptiveQuestion)
        .where(AdaptiveQuestion.topic == topic)
        .where(AdaptiveQuestion.difficulty >= difficulty - 0.2)
        .where(AdaptiveQuestion.difficulty <= difficulty + 0.2)
        .order_by(func.random())
        .limit(1)
    )
    question = result.scalar_one_or_none()

    if not question:
        return None

    return {
        "id": question.id,
        "question": question.question_text,
        "options": question.options,
        "difficulty": question.difficulty
    }

@app.get("/api/adaptive/lesson-questions")
async def get_adaptive_lesson_questions(topic: str, count: int, userId: str, db: AsyncSession = Depends(get_db)):
    """Вопросы урока"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем вопросы по теме
    result = await db.execute(
        select(AdaptiveQuestion)
        .where(AdaptiveQuestion.topic == topic)
        .order_by(func.random())
        .limit(count)
    )
    questions = result.scalars().all()

    questions_list = []
    for q in questions:
        questions_list.append({
            "id": q.id,
            "question": q.question_text,
            "options": q.options,
            "difficulty": q.difficulty
        })

    return questions_list

@app.post("/api/adaptive/answer")
async def record_adaptive_answer(request: AdaptiveAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Записать ответ"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем или создаем мастерство по теме
    result = await db.execute(
        select(AdaptiveMastery)
        .where(AdaptiveMastery.user_id == user.id)
        .where(AdaptiveMastery.topic == request.topic)
    )
    mastery = result.scalar_one_or_none()

    if not mastery:
        mastery = AdaptiveMastery(
            user_id=user.id,
            topic=request.topic,
            mastery_level=0.0,
            correct_answers=0,
            total_answers=0
        )
        db.add(mastery)

    # Обновляем статистику
    mastery.total_answers += 1
    if request.isCorrect:
        mastery.correct_answers += 1

    # Пересчитываем уровень мастерства (простая формула)
    mastery.mastery_level = mastery.correct_answers / mastery.total_answers if mastery.total_answers > 0 else 0.0
    mastery.last_practiced = datetime.utcnow()

    # Начисляем XP за правильный ответ
    if request.isCorrect:
        user.xp += 10
        user.last_activity = datetime.utcnow()

    await db.commit()

    logger.info(f"User {user.username} answered question on topic {request.topic}: {'correct' if request.isCorrect else 'incorrect'}")

    return {
        "success": True,
        "new_mastery": mastery.mastery_level,
        "xp_earned": 10 if request.isCorrect else 0
    }

@app.get("/api/adaptive/generate-question")
async def generate_question(userId: str, topic: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Генерация вопроса"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Если тема не указана, выбираем самую слабую
    if not topic:
        result = await db.execute(
            select(AdaptiveMastery)
            .where(AdaptiveMastery.user_id == user.id)
            .order_by(AdaptiveMastery.mastery_level)
            .limit(1)
        )
        mastery = result.scalar_one_or_none()
        topic = mastery.topic if mastery else "Основы финансов"

    # Получаем мастерство
    result = await db.execute(
        select(AdaptiveMastery)
        .where(AdaptiveMastery.user_id == user.id)
        .where(AdaptiveMastery.topic == topic)
    )
    mastery = result.scalar_one_or_none()

    difficulty = mastery.mastery_level + 0.1 if mastery else 0.3

    try:
        # Генерируем вопрос через LLM
        question_data = await generate_adaptive_question_with_llm(topic, difficulty)

        # Сохраняем вопрос в базу
        question = AdaptiveQuestion(
            topic=topic,
            question_text=question_data["question"],
            options=question_data["options"],
            correct_answer=question_data["correct"],
            difficulty=difficulty
        )
        db.add(question)
        await db.commit()
        await db.refresh(question)

        return {
            "id": question.id,
            "question": question.question_text,
            "options": question.options,
            "topic": topic,
            "difficulty": difficulty
        }

    except Exception as e:
        logger.error(f"Error generating question: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate question")

@app.post("/api/v2/generate-lesson")
async def generate_lesson(request: GenerateLessonRequest, db: AsyncSession = Depends(get_db)):
    """Генерация урока"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Генерируем урок через LLM
        lesson_data = await generate_lesson_with_llm(request.weakTopic, request.strongTopic)

        # Сохраняем урок в базу (опционально, можно создать динамический модуль)
        # Для MVP просто возвращаем сгенерированный урок

        logger.info(f"Generated lesson for user {user.username}: {lesson_data['title']}")

        return {
            "title": lesson_data["title"],
            "content": lesson_data["content"],
            "questions": lesson_data["questions"],
            "xp_reward": lesson_data["xp_reward"]
        }

    except Exception as e:
        logger.error(f"Error generating lesson: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate lesson")

@app.get("/api/v2/ai-advice")
async def get_ai_advice(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить AI советы для пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Получаем транзакции за последний месяц
        from datetime import datetime, timedelta
        month_ago = datetime.utcnow() - timedelta(days=30)
        
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .where(Transaction.timestamp >= month_ago)
            .order_by(desc(Transaction.timestamp))
        )
        transactions = result.scalars().all()
        
        total_expenses = sum(t.amount for t in transactions)
        
        # Генерируем советы
        tips = []
        
        if user.current_balance < 1000:
            tips.append({
                "icon": "⚠️",
                "text": "Баланс критически низкий! Сократите расходы и найдите дополнительные источники дохода."
            })
        elif total_expenses > user.current_balance * 0.5:
            tips.append({
                "icon": "💡",
                "text": "Вы тратите больше половины баланса в месяц. Рекомендую создать бюджет и придерживаться его."
            })
        else:
            tips.append({
                "icon": "✅",
                "text": "Отличная работа! Ваши траты под контролем. Продолжайте в том же духе!"
            })
        
        # Анализ по категориям
        spending_by_category = {}
        for t in transactions:
            cat = t.category.value
            spending_by_category[cat] = spending_by_category.get(cat, 0) + t.amount
        
        if spending_by_category.get("food", 0) > total_expenses * 0.4:
            tips.append({
                "icon": "🍔",
                "text": "Расходы на еду составляют более 40%. Попробуйте готовить дома чаще — сэкономите до 30%."
            })
        
        if spending_by_category.get("entertainment", 0) > total_expenses * 0.3:
            tips.append({
                "icon": "🎮",
                "text": "Много трат на развлечения. Рекомендую сократить их на 20% и направить в накопления."
            })
        
        tips.append({
            "icon": "📊",
            "text": f"Финансовый скоринг: {user.financial_score}/1000. Продолжайте улучшать свои финансовые привычки!"
        })
        
        return {
            "tips": tips,
            "balance": user.current_balance,
            "total_expenses": total_expenses,
            "financial_score": user.financial_score
        }
        
    except Exception as e:
        logger.error(f"Error generating AI advice: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate advice")

@app.post("/api/v2/ai-chat")
async def ai_chat(request: dict, db: AsyncSession = Depends(get_db)):
    """AI чат для финансовых советов"""
    user_id = request.get("userId")
    message = request.get("message", "")
    
    result = await db.execute(select(User).where(User.username == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Получаем контекст пользователя
        from datetime import datetime, timedelta
        month_ago = datetime.utcnow() - timedelta(days=30)
        
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .where(Transaction.timestamp >= month_ago)
            .order_by(desc(Transaction.timestamp))
            .limit(20)
        )
        transactions = result.scalars().all()
        
        total_expenses = sum(t.amount for t in transactions if t.transaction_type == "expense")
        total_income = sum(t.amount for t in transactions if t.transaction_type == "income")
        
        # Формируем контекст для LLM
        context = f"""Пользователь: {user.name}
Баланс: {user.current_balance} ₽
Доходы за месяц: {total_income} ₽
Расходы за месяц: {total_expenses} ₽
Уровень: {user.level}
Финансовый скоринг: {user.financial_score}/1000

Последние транзакции:
"""
        for t in transactions[:5]:
            context += f"- {t.transaction_type}: {t.amount} ₽ ({t.category.value})\n"
        
        # Вызываем LLM
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key or api_key == "":
            # Fallback без LLM
            responses = [
                "Отличный вопрос! Рекомендую сократить расходы на развлечения на 20% и направить эти деньги в накопления.",
                "Судя по твоим тратам, ты тратишь много на еду вне дома. Попробуй готовить дома чаще — сэкономишь до 30%.",
                f"Твой баланс {user.current_balance} ₽ стабилен! Продолжай в том же духе и не забывай откладывать 10-15% от дохода.",
                "Заметил, что в этом месяце расходы выросли. Проверь свои категории — там можно оптимизировать.",
            ]
            import random
            return {"response": random.choice(responses)}
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        prompt = f"""{context}

Вопрос пользователя: {message}

Ты - финансовый AI-советник для подростков и молодежи. Отвечай кратко (2-3 предложения), понятно, дружелюбно. Используй эмодзи. Давай конкретные советы на основе данных пользователя."""
        
        response = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=[
                {"role": "system", "content": "Ты финансовый советник для молодежи. Отвечай кратко, понятно, с эмодзи."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        ai_response = response.choices[0].message.content
        
        logger.info(f"AI chat response for user {user.username}: {ai_response[:50]}...")
        
        return {"response": ai_response}
        
    except Exception as e:
        logger.error(f"Error in AI chat: {str(e)}")
        # Fallback
        return {"response": f"Привет! У тебя сейчас {user.current_balance} ₽ на балансе. Чем могу помочь? 💰"}
