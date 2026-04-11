"""API Gateway - Port 8000"""
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, EmailStr, constr, validator
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import sys
import uuid
import os
sys.path.append('/app')

from shared.redis import get_cache, set_cache, rate_limit, delete_cache
from shared.schemas import TransactionCreate, TransactionResponse, PredictionResponse, DashboardResponse
from shared.db import get_db
from shared.models import User
from shared.startup import validate_startup
from shared.logger import setup_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from auth_utils import hash_password, verify_password, create_access_token, get_user_id_from_token, is_admin_email

# Validate configuration on startup
config = validate_startup()
logger = setup_logger("gateway")

# Middleware classes
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app = FastAPI(title="Gateway")

# Add security middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Auth schemas with validation
class RegisterRequest(BaseModel):
    email: EmailStr
    name: constr(min_length=2, max_length=100)
    password: constr(min_length=8, max_length=128)

    @validator('password')
    def password_strength(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    is_admin: bool = False

# CORS configuration - restrict origins in production
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost,http://localhost:80,http://localhost:3000,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An internal error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

TRANSACTIONS_URL = "http://transactions:8001"
AI_URL = "http://ai:8002"

# Category mapping
CATEGORY_MAP = {
    "food": "Еда",
    "transport": "Транспорт",
    "entertainment": "Развлечения",
    "education": "Образование",
    "salary": "Зарплата",
    "other": "Другое"
}

CATEGORY_ICONS = {
    "food": "🍔",
    "transport": "🚗",
    "entertainment": "🎮",
    "education": "📚",
    "salary": "💰",
    "other": "💸"
}


@app.get("/health")
async def health():
    return {"status": "ok"}


# Auth endpoints
@app.post("/api/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Rate limit registration attempts
    if not await rate_limit(f"auth:register:{req.email}", max_req=5, window=300):
        raise HTTPException(429, "Too many registration attempts. Try again in 5 minutes.")

    # Check if user exists
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "User already exists")

    # Create user with bcrypt hashed password
    password_hash = hash_password(req.password)
    user = User(
        email=req.email,
        username=req.name,
        password_hash=password_hash,
        balance=5000.0  # Starting balance
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create JWT token
    is_admin = is_admin_email(req.email)
    token = create_access_token(user.id, req.email, is_admin)

    return {"access_token": token, "is_admin": is_admin}


@app.post("/api/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Rate limit login attempts to prevent brute force
    if not await rate_limit(f"auth:login:{req.email}", max_req=10, window=300):
        raise HTTPException(429, "Too many login attempts. Try again in 5 minutes.")

    # Find user
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # Verify password with bcrypt
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid password")

    # Create JWT token
    is_admin = is_admin_email(req.email)
    token = create_access_token(user.id, req.email, is_admin)

    return {"access_token": token, "is_admin": is_admin}



@app.post("/api/transactions")
async def create_transaction(txn: TransactionCreate):
    if not await rate_limit(txn.user_id):
        raise HTTPException(429, "Rate limit exceeded")

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/transactions", json=txn.model_dump(mode='json'))
        resp.raise_for_status()
        result = resp.json()

        # Add category mapping
        if result.get("category"):
            result["category"] = CATEGORY_MAP.get(result["category"], result["category"])
            result["category_icon"] = CATEGORY_ICONS.get(result.get("category", "").lower(), "💰")
        result["comment"] = result.get("description", "")
        result["date"] = result.get("timestamp", "")

        # Invalidate cache
        await delete_cache(f"dashboard:{txn.user_id}")

        return result


@app.get("/api/transactions")
async def get_transactions(userId: str, limit: int = 30):
    # Support query param userId
    user_id = int(userId) if userId.isdigit() else 1

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/transactions/{user_id}?limit={limit}")
        resp.raise_for_status()
        transactions = resp.json()

        # Map categories to Russian
        for txn in transactions:
            if txn.get("category"):
                eng_cat = txn["category"]
                txn["category"] = CATEGORY_MAP.get(eng_cat, eng_cat)
                txn["category_icon"] = CATEGORY_ICONS.get(eng_cat, "💰")
            txn["comment"] = txn.get("description", "")
            txn["date"] = txn.get("timestamp", "")

        return transactions


@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int, userId: str):
    user_id = int(userId) if userId.isdigit() else 1

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.delete(f"{TRANSACTIONS_URL}/transactions/{transaction_id}?userId={user_id}")
        resp.raise_for_status()

        # Invalidate cache
        await delete_cache(f"dashboard:{user_id}")

        return resp.json()


@app.get("/api/dashboard/{user_id}")
async def get_dashboard(user_id: int):
    cache_key = f"dashboard:{user_id}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=5.0) as client:
        balance_resp = await client.get(f"{TRANSACTIONS_URL}/balance/{user_id}")
        txns_resp = await client.get(f"{TRANSACTIONS_URL}/transactions/{user_id}?limit=10")

        try:
            pred_resp = await client.get(f"{AI_URL}/predict/{user_id}")
            prediction = pred_resp.json() if pred_resp.status_code == 200 else None
        except httpx.HTTPError as e:
            logger.warning(f"AI prediction unavailable for user {user_id}: {e}")
            prediction = None
        except Exception as e:
            logger.error(f"Unexpected error fetching prediction for user {user_id}: {e}", exc_info=True)
            prediction = None

        balance_resp.raise_for_status()
        txns_resp.raise_for_status()

        balance_data = balance_resp.json()
        transactions = txns_resp.json()

        # Calculate spending by category for chart
        spending_chart = []
        category_totals = {}
        for txn in transactions:
            if txn.get("type") == "expense":
                cat = txn.get("category", "other")
                category_totals[cat] = category_totals.get(cat, 0) + txn.get("amount", 0)

        for cat, amount in category_totals.items():
            spending_chart.append({
                "category": CATEGORY_MAP.get(cat, cat),
                "amount": amount,
                "icon": CATEGORY_ICONS.get(cat, "💸")
            })

        # Generate AI tips
        ai_tips = []
        if prediction:
            risk = prediction.get("risk_level", "safe")
            if risk == "critical":
                ai_tips.append("🚨 Срочно сократите расходы!")
                ai_tips.append("💡 Пересмотрите ежедневные траты")
            elif risk == "danger":
                ai_tips.append("⚠️ Контролируйте бюджет внимательнее")
                ai_tips.append("📊 Проанализируйте крупные расходы")
            else:
                ai_tips.append("✅ Финансы под контролем")
                ai_tips.append("💰 Продолжайте откладывать")

        # Calculate stats
        categories_used = len(set(txn.get("category") for txn in transactions if txn.get("type") == "expense"))
        savings_rate = 0
        if balance_data.get("total_income", 0) > 0:
            savings = balance_data.get("total_income", 0) - balance_data.get("total_expenses", 0)
            savings_rate = int((savings / balance_data.get("total_income", 1)) * 100)

        # Transform to frontend format
        dashboard = {
            "balance": {
                "current": balance_data.get("balance", 0)
            },
            "income": {
                "month": balance_data.get("total_income", 0)
            },
            "expenses": {
                "month": balance_data.get("total_expenses", 0)
            },
            "transactions": transactions,
            "forecast": None,
            "ai_tips": ai_tips,
            "spending_chart": spending_chart,
            "stats": {
                "transactions_count": balance_data.get("transaction_count", 0),
                "savings_rate": savings_rate,
                "categories_used": categories_used,
                "achievements": 0
            }
        }

        # Add forecast from prediction
        if prediction and prediction.get("days_left"):
            days_left = int(prediction["days_left"])
            daily_avg = int(balance_data.get("balance", 0) / days_left) if days_left > 0 else 0
            dashboard["forecast"] = {
                "days_left": days_left,
                "daily_avg": daily_avg
            }

        await set_cache(cache_key, dashboard, ttl=60)
        return dashboard


@app.post("/api/predict/{user_id}", response_model=PredictionResponse)
async def trigger_prediction(user_id: int):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{AI_URL}/predict/{user_id}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/predict/{user_id}", response_model=PredictionResponse)
async def get_prediction(user_id: int):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{AI_URL}/predict/{user_id}")
        if resp.status_code == 404:
            raise HTTPException(404, "No prediction found")
        resp.raise_for_status()
        return resp.json()


# Gamification - proxy to transaction service
@app.get("/api/achievements")
async def get_achievements(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/achievements?userId={userId}")
        return resp.json() if resp.status_code == 200 else []


@app.get("/api/daily-missions")
async def get_daily_missions(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/daily-missions?userId={userId}")
        return resp.json() if resp.status_code == 200 else []


@app.get("/api/progress")
async def get_progress(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/progress?userId={userId}")
        return resp.json() if resp.status_code == 200 else {"level": 1, "xp": 0, "next_level_xp": 100}


# Portfolio endpoints - proxy to transaction service
@app.get("/api/portfolio")
async def get_portfolio(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/portfolio?userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.post("/api/trade")
async def trade(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/trade", json=data)
        resp.raise_for_status()
        return resp.json()


@app.get("/api/stocks")
async def get_stocks(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/stocks?userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/stock/{ticker}")
async def get_stock_detail(ticker: str, userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/stock/{ticker}?userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.post("/api/check-portfolio")
async def check_portfolio(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/check-portfolio?userId={data.get('userId', '1')}")
        resp.raise_for_status()
        return resp.json()


@app.post("/api/reset-portfolio")
async def reset_portfolio(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/reset-portfolio?userId={data.get('userId', '1')}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/recommendations")
async def get_recommendations(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/recommendations?userId={userId}")
        resp.raise_for_status()
        return resp.json()


# Market events
@app.get("/api/market-event")
async def get_market_event(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/market-event?userId={userId}")
        return resp.json() if resp.status_code == 200 else None


@app.post("/api/market-event/action")
async def market_event_action(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/market-event/action", json=data)
        resp.raise_for_status()
        return resp.json()


# Learning system
@app.get("/api/v2/modules")
async def get_modules(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/v2/modules?userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/v2/lessons")
async def get_lessons(userId: str, moduleId: int):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/v2/lessons?userId={userId}&moduleId={moduleId}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/v2/lesson/{lesson_id}")
async def get_lesson_detail(lesson_id: int, userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/v2/lesson/{lesson_id}?userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.post("/api/v2/complete-lesson")
async def complete_lesson(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/v2/complete-lesson", json=data)
        resp.raise_for_status()
        return resp.json()


@app.post("/api/v2/generate-lesson")
async def generate_lesson(userId: str, weakTopic: str = None, strongTopic: str = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{TRANSACTIONS_URL}/v2/generate-lesson?userId={userId}"
        if weakTopic:
            url += f"&weakTopic={weakTopic}"
        if strongTopic:
            url += f"&strongTopic={strongTopic}"
        resp = await client.post(url)
        resp.raise_for_status()
        return resp.json()


# Adaptive AI
@app.get("/api/adaptive/mastery")
async def get_mastery(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/adaptive/mastery?userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/adaptive/recommendation")
async def get_adaptive_recommendation(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/adaptive/recommendation?userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/adaptive/next-question")
async def get_next_question(topic: str, userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/adaptive/next-question?topic={topic}&userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/adaptive/lesson-questions")
async def get_lesson_questions(topic: str, count: int, userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/adaptive/lesson-questions?topic={topic}&count={count}&userId={userId}")
        resp.raise_for_status()
        return resp.json()


@app.post("/api/adaptive/answer")
async def record_adaptive_answer(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/adaptive/answer", json=data)
        resp.raise_for_status()
        return resp.json()


@app.post("/api/adaptive/generate-question")
async def generate_adaptive_question(userId: str, topic: str = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{TRANSACTIONS_URL}/adaptive/generate-question?userId={userId}"
        if topic:
            url += f"&topic={topic}"
        resp = await client.post(url)
        resp.raise_for_status()
        return resp.json()


# Other endpoints
@app.get("/api/diary")
async def get_diary(userId: str, limit: int = 20):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/diary?userId={userId}&limit={limit}")
        return resp.json() if resp.status_code == 200 else []


@app.get("/api/levels")
async def get_levels():
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/levels")
        resp.raise_for_status()
        return resp.json()


@app.post("/api/buy-freeze")
async def buy_freeze(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/buy-freeze", json=data)
        resp.raise_for_status()
        return resp.json()


@app.get("/api/experience")
async def get_experience(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/experience?userId={userId}")
        return resp.json() if resp.status_code == 200 else {"level": 1, "xp": 0}


@app.post("/api/interactions")
async def post_interaction(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/interactions", json=data)
        return resp.json() if resp.status_code == 200 else {"status": "ok"}


@app.get("/api/onboarding/questions")
async def get_onboarding_questions():
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/onboarding/questions")
        return resp.json() if resp.status_code == 200 else []


@app.get("/api/onboarding/status")
async def get_onboarding_status(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/onboarding/status?userId={userId}")
        return resp.json() if resp.status_code == 200 else {"completed": True}


@app.post("/api/onboarding/submit")
async def submit_onboarding(data: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/onboarding/submit", json=data)
        return resp.json() if resp.status_code == 200 else {"status": "ok"}


@app.get("/api/onboarding/result")
async def get_onboarding_result(userId: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/onboarding/result?userId={userId}")
        return resp.json() if resp.status_code == 200 else {"score": 0, "level": "beginner"}
