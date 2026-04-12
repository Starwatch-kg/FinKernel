"""Onboarding System Routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import sys

sys.path.append("/app")

from shared.db import get_db
from shared.models import User
from pydantic import BaseModel

router = APIRouter()


class OnboardingSubmit(BaseModel):
    userId: str
    answers: dict


ONBOARDING_QUESTIONS = [
    {
        "id": 1,
        "question": "Какой у вас опыт в инвестициях?",
        "type": "single",
        "options": [
            {"id": "a", "text": "Никогда не инвестировал", "score": 0},
            {"id": "b", "text": "Начинающий инвестор", "score": 1},
            {"id": "c", "text": "Опытный инвестор", "score": 2},
        ],
    },
    {
        "id": 2,
        "question": "Как вы относитесь к риску?",
        "type": "single",
        "options": [
            {"id": "a", "text": "Избегаю риска", "score": 0},
            {"id": "b", "text": "Умеренный риск", "score": 1},
            {"id": "c", "text": "Готов рисковать", "score": 2},
        ],
    },
    {
        "id": 3,
        "question": "Какая ваша финансовая цель?",
        "type": "single",
        "options": [
            {"id": "a", "text": "Сохранить деньги", "score": 0},
            {"id": "b", "text": "Накопить на покупку", "score": 1},
            {"id": "c", "text": "Создать пассивный доход", "score": 2},
        ],
    },
]


@router.get("/onboarding/questions")
async def get_onboarding_questions():
    """Get onboarding questions"""
    return ONBOARDING_QUESTIONS


@router.get("/onboarding/status")
async def get_onboarding_status(userId: str, db: AsyncSession = Depends(get_db)):
    """Check if user completed onboarding"""
    user_id = int(userId) if userId.isdigit() else 1

    # For now, always return completed
    # In production, would check user profile
    return {"completed": True}


@router.post("/onboarding/submit")
async def submit_onboarding(data: OnboardingSubmit, db: AsyncSession = Depends(get_db)):
    """Submit onboarding answers"""
    user_id = int(data.userId) if data.userId.isdigit() else 1

    # Calculate score
    total_score = 0
    for answer in data.answers.values():
        # Simple scoring logic
        if answer == "c":
            total_score += 2
        elif answer == "b":
            total_score += 1

    # Determine level
    if total_score <= 2:
        level = "beginner"
    elif total_score <= 4:
        level = "intermediate"
    else:
        level = "advanced"

    return {"status": "completed", "score": total_score, "level": level}


@router.get("/onboarding/result")
async def get_onboarding_result(userId: str, db: AsyncSession = Depends(get_db)):
    """Get onboarding result"""
    user_id = int(userId) if userId.isdigit() else 1

    # Return default result
    return {
        "score": 3,
        "level": "intermediate",
        "recommendations": [
            "Начните с базовых уроков",
            "Изучите основы инвестирования",
            "Практикуйтесь с виртуальным портфелем",
        ],
    }
