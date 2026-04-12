"""Onboarding System Routes"""

import sys
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from pydantic import BaseModel
from shared.db import get_db
from shared.models import User

router = APIRouter()


class OnboardingSubmit(BaseModel):
    userId: str
    answers: dict


ONBOARDING_QUESTIONS = [
    {
        "id": 1,
        "question": "Какой у вас ежемесячный доход?",
        "type": "input",
        "input_type": "number",
        "placeholder": "Введите сумму в сомах",
        "min": 0,
        "max": 10000000,
    },
    {
        "id": 2,
        "question": "Какая ваша основная финансовая цель?",
        "type": "single",
        "options": [
            {"id": "a", "text": "Накопить на крупную покупку", "goal": "purchase"},
            {"id": "b", "text": "Создать финансовую подушку безопасности", "goal": "emergency"},
            {"id": "c", "text": "Инвестировать и приумножить капитал", "goal": "invest"},
            {"id": "d", "text": "Погасить долги и кредиты", "goal": "debt"},
            {"id": "e", "text": "Просто контролировать расходы", "goal": "control"},
        ],
    },
    {
        "id": 3,
        "question": "Сколько процентов от дохода вы хотите откладывать?",
        "type": "input",
        "input_type": "number",
        "placeholder": "Введите процент (0-100)",
        "min": 0,
        "max": 100,
        "suffix": "%",
    },
    {
        "id": 4,
        "question": "Какие категории расходов для вас наиболее важны?",
        "type": "multiple",
        "options": [
            {"id": "a", "text": "Еда и продукты", "category": "food"},
            {"id": "b", "text": "Транспорт", "category": "transport"},
            {"id": "c", "text": "Жилье и коммунальные услуги", "category": "housing"},
            {"id": "d", "text": "Развлечения и отдых", "category": "entertainment"},
            {"id": "e", "text": "Образование и саморазвитие", "category": "education"},
            {"id": "f", "text": "Здоровье и спорт", "category": "health"},
        ],
    },
    {
        "id": 5,
        "question": "Как часто вы получаете доход?",
        "type": "single",
        "options": [
            {"id": "a", "text": "Раз в месяц (зарплата)", "frequency": "monthly"},
            {"id": "b", "text": "Два раза в месяц", "frequency": "biweekly"},
            {"id": "c", "text": "Каждую неделю", "frequency": "weekly"},
            {"id": "d", "text": "Нерегулярно (фриланс)", "frequency": "irregular"},
        ],
    },
]


@router.get("/onboarding/questions")
async def get_onboarding_questions():
    """Get onboarding questions"""
    return {"questions": ONBOARDING_QUESTIONS}


@router.get("/onboarding/status")
async def get_onboarding_status(userId: str, db: AsyncSession = Depends(get_db)):
    """Check if user completed onboarding"""
    user_id = int(userId) if userId.isdigit() else 1

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"completed": False}

    # Check if user has onboarding data
    has_profile = user.monthly_income is not None
    return {"completed": has_profile}


@router.post("/onboarding/submit")
async def submit_onboarding(data: OnboardingSubmit, db: AsyncSession = Depends(get_db)):
    """Submit onboarding answers and save user profile"""
    user_id = int(data.userId) if data.userId.isdigit() else 1

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Parse answers
    answers = data.answers

    # Extract income (question 1) - now direct input
    income_answer = answers.get("1")
    monthly_income = None
    if income_answer:
        try:
            monthly_income = float(income_answer)
        except (ValueError, TypeError):
            monthly_income = None

    # Extract goal (question 2)
    goal_answer = answers.get("2")
    financial_goal = None
    if goal_answer:
        goal_options = ONBOARDING_QUESTIONS[1]["options"]
        selected = next((opt for opt in goal_options if opt["id"] == goal_answer), None)
        if selected:
            financial_goal = selected.get("goal")

    # Extract savings percent (question 3) - now direct input
    savings_answer = answers.get("3")
    savings_percent = 10  # default
    if savings_answer:
        try:
            savings_percent = float(savings_answer)
            # Clamp between 0 and 100
            savings_percent = max(0, min(100, savings_percent))
        except (ValueError, TypeError):
            savings_percent = 10

    # Extract categories (question 4)
    categories_answer = answers.get("4", [])
    if isinstance(categories_answer, str):
        categories_answer = [categories_answer]

    # Extract income frequency (question 5)
    frequency_answer = answers.get("5")
    income_frequency = "monthly"
    if frequency_answer:
        freq_options = ONBOARDING_QUESTIONS[4]["options"]
        selected = next((opt for opt in freq_options if opt["id"] == frequency_answer), None)
        if selected:
            income_frequency = selected.get("frequency", "monthly")

    # Update user profile
    user.monthly_income = monthly_income
    user.financial_goal = financial_goal
    user.savings_target_percent = savings_percent
    user.income_frequency = income_frequency
    user.onboarding_completed = True
    user.onboarding_completed_at = datetime.utcnow()

    await db.commit()

    # Generate recommendations
    recommendations = []

    if monthly_income and savings_percent > 0:
        target_savings = monthly_income * (savings_percent / 100)
        recommendations.append(f"Откладывайте {int(target_savings):,} с каждый месяц")

    if financial_goal == "emergency":
        recommendations.append("Создайте подушку безопасности на 3-6 месяцев расходов")
    elif financial_goal == "invest":
        recommendations.append("Начните с малых инвестиций и изучите основы")
    elif financial_goal == "debt":
        recommendations.append("Сначала погасите долги с высокими процентами")

    recommendations.append("Отслеживайте все расходы для полной картины")
    recommendations.append("Используйте AI-советника для персональных рекомендаций")

    return {
        "status": "completed",
        "profile": {
            "monthly_income": monthly_income,
            "financial_goal": financial_goal,
            "savings_percent": savings_percent,
            "income_frequency": income_frequency,
        },
        "recommendations": recommendations,
        "xp_bonus": 100,
    }
