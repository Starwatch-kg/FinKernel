"""
Роутер для аутентификации
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core import get_db, hash_password, verify_password
from backend.models import User
from backend.schemas import RegisterRequest, LoginRequest, AuthResponse

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Регистрация пользователя с хешированием пароля"""
    result = await db.execute(select(User).where(User.email == request.email))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Хешируем пароль
    hashed_password = hash_password(request.password)

    user = User(
        username=request.email,
        email=request.email,
        name=request.name,
        password_hash=hashed_password,
        current_balance=10000.0,
        financial_score=500,
        level=1,
        xp=0,
        streak=0
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return AuthResponse(
        access_token=f"user_{user.id}",
        name=request.name,
        email=request.email,
        is_admin=request.email == "admin@admin.com"
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Вход пользователя с проверкой пароля"""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.username == request.email))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем пароль (если есть хеш)
    if user.password_hash:
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")

    return AuthResponse(
        access_token=f"user_{user.id}",
        name=user.name or user.username,
        email=user.email or user.username,
        is_admin=(user.email == "admin@admin.com" or user.username == "admin@admin.com")
    )


@router.post("/user/create")
async def create_user(username: str, initial_balance: float = 10000.0, db: AsyncSession = Depends(get_db)):
    """Legacy endpoint для создания пользователя"""
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


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """Список всех пользователей"""
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
