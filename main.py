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
    Module, Lesson, LessonProgress, get_db, init_db
)
from llm_agent import parse_transaction_with_llm, evaluate_purchase_with_llm

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Financial AI Assistant")

# CORS из переменных окружения
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

class AddTransactionRequest(BaseModel):
    userId: str
    amount: float
    category: str
    description: Optional[str] = None

class CompleteLessonRequest(BaseModel):
    userId: str
    lessonId: int
    correctAnswers: int = 0
    totalQuestions: int = 0

class OnboardingSubmitRequest(BaseModel):
    userId: str
    answers: dict

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
                "amount": -t.amount,
                "category": t.category.value,
                "timestamp": t.timestamp.isoformat(),
                "description": t.description or f"Покупка в категории {t.category.value}"
            }
            for t in recent_transactions
        ],
        "forecast": {
            "days_left": days_left,
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
            "amount": -t.amount,
            "category": t.category.value,
            "timestamp": t.timestamp.isoformat(),
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

    transaction = Transaction(
        user_id=user.id,
        amount=abs(request.amount),
        category=cat,
        description=request.description
    )
    db.add(transaction)

    # Обновляем баланс и XP
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
            "title": achievement.title,
            "description": achievement.description,
            "icon": achievement.icon,
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

# ============ Portfolio (заглушка для совместимости) ============

@app.get("/api/portfolio")
async def get_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Портфолио пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "cash": user.current_balance,
        "stocks": [],
        "total_value": user.current_balance
    }

@app.post("/api/check-portfolio")
async def check_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Проверить портфолио"""
    return {"status": "ok"}

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
async def get_daily_missions(userId: str):
    """Ежедневные миссии (заглушка)"""
    return []

@app.post("/api/buy-freeze")
async def buy_freeze(userId: str):
    """Покупка заморозки (заглушка)"""
    return {"success": False, "message": "Feature not implemented"}

@app.get("/api/stocks")
async def get_stocks(userId: str):
    """Список акций (заглушка)"""
    return []

@app.get("/api/stock/{ticker}")
async def get_stock_detail(ticker: str, userId: str):
    """Детали акции (заглушка)"""
    return {"ticker": ticker, "price": 0, "change": 0}

@app.get("/api/market-event")
async def get_market_event(userId: str):
    """Рыночные события (заглушка)"""
    return None

@app.get("/api/recommendations")
async def get_recommendations(userId: str):
    """Рекомендации (заглушка)"""
    return []

@app.post("/api/market-event/action")
async def market_event_action(userId: str, eventId: int, action: str):
    """Действие на событие (заглушка)"""
    return {"success": False}

@app.post("/api/trade")
async def trade(userId: str, ticker: str, shares: int, action: str):
    """Торговля акциями (заглушка)"""
    return {"success": False, "message": "Trading not implemented"}

@app.post("/api/reset-portfolio")
async def reset_portfolio(userId: str):
    """Сброс портфолио (заглушка)"""
    return {"success": False}

@app.get("/api/experience")
async def get_experience(userId: str):
    """Опыт пользователя (legacy, заглушка)"""
    return {"xp": 0, "level": 1}

@app.post("/api/interactions")
async def post_interaction(userId: str, cardId: int, answer_index: int):
    """Взаимодействия (legacy, заглушка)"""
    return {"success": False}

# ============ Adaptive Learning (заглушки) ============

@app.get("/api/adaptive/mastery")
async def get_adaptive_mastery(userId: str):
    """Адаптивное обучение - мастерство (заглушка)"""
    return {}

@app.get("/api/adaptive/recommendation")
async def get_adaptive_recommendation(userId: str):
    """Адаптивные рекомендации (заглушка)"""
    return None

@app.get("/api/adaptive/next-question")
async def get_adaptive_next_question(topic: str, userId: str):
    """Следующий вопрос (заглушка)"""
    return None

@app.get("/api/adaptive/lesson-questions")
async def get_adaptive_lesson_questions(topic: str, count: int, userId: str):
    """Вопросы урока (заглушка)"""
    return []

@app.post("/api/adaptive/answer")
async def record_adaptive_answer(userId: str, topic: str, questionId: int, isCorrect: bool, timeMs: int = 0, source: str = "lesson"):
    """Записать ответ (заглушка)"""
    return {"success": False}

@app.get("/api/adaptive/generate-question")
async def generate_question(userId: str, topic: Optional[str] = None):
    """Генерация вопроса (заглушка)"""
    return None

@app.post("/api/v2/generate-lesson")
async def generate_lesson(userId: str, weakTopic: Optional[str] = None, strongTopic: Optional[str] = None):
    """Генерация урока (заглушка)"""
    return None
