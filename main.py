from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import List
from datetime import datetime

from models import User, Transaction, TransactionCategory, get_db, init_db
from llm_agent import parse_transaction_with_llm, evaluate_purchase_with_llm

app = FastAPI(title="Financial AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173", "http://localhost:3000"],
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

class LoginRequest(BaseModel):
    email: str
    password: str

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
    """Дашборд для фронтенда - адаптер к существующему API"""
    # Пытаемся найти пользователя по username (userId в фронтенде - это email/username)
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем транзакции
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.timestamp))
        .limit(10)
    )
    transactions = result.scalars().all()

    # Считаем доходы и расходы
    expenses = sum(t.amount for t in transactions)
    income = 0  # Пока нет доходов в модели

    return {
        "balance": user.current_balance,
        "income": income,
        "expenses": expenses,
        "transactions": [
            {
                "id": t.id,
                "amount": -t.amount,  # Отрицательное для расходов
                "category": t.category.value,
                "timestamp": t.timestamp.isoformat(),
                "description": f"Покупка в категории {t.category.value}"
            }
            for t in transactions
        ],
        "forecast": {
            "days_left": 30,
            "message": "При текущих тратах денег хватит на месяц"
        },
        "ai_tips": [
            "Отличная работа! Продолжайте в том же духе.",
            f"Ваш финансовый скоринг: {user.financial_score}/1000"
        ],
        "spending_chart": [
            {"category": "food", "amount": sum(t.amount for t in transactions if t.category.value == "food")},
            {"category": "transport", "amount": sum(t.amount for t in transactions if t.category.value == "transport")},
            {"category": "entertainment", "amount": sum(t.amount for t in transactions if t.category.value == "entertainment")},
            {"category": "other", "amount": sum(t.amount for t in transactions if t.category.value == "other")}
        ],
        "stats": {
            "level": user.financial_score // 100,
            "xp": user.financial_score % 100,
            "streak": 0
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
            "description": f"Покупка в категории {t.category.value}"
        }
        for t in transactions
    ]

@app.post("/api/register")
async def register_frontend(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Регистрация пользователя"""
    # Проверяем, существует ли пользователь
    result = await db.execute(select(User).where(User.username == request.email))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Создаем пользователя
    user = User(username=request.email, current_balance=10000.0, financial_score=500)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "access_token": "dummy_token",  # Временно без JWT
        "name": request.name,
        "email": request.email,
        "is_admin": request.email == "admin@admin.com"
    }

@app.post("/api/login")
async def login_frontend(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Вход пользователя"""
    result = await db.execute(select(User).where(User.username == request.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "access_token": "dummy_token",  # Временно без JWT
        "name": user.username,
        "email": user.username,
        "is_admin": request.email == "admin@admin.com"
    }

# Заглушки для остальных эндпоинтов
@app.get("/api/portfolio")
async def get_portfolio(userId: str):
    return {"cash": 10000, "stocks": [], "total_value": 10000}

@app.get("/api/v2/modules")
async def get_modules(userId: str):
    return []

@app.get("/api/achievements")
async def get_achievements(userId: str):
    return {"achievements": [], "daily_missions": []}

@app.get("/api/onboarding/status")
async def get_onboarding_status(userId: str):
    return {"completed": True}

@app.post("/api/check-portfolio")
async def check_portfolio(userId: str):
    return {"status": "ok"}

