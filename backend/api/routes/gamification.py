"""
Роутер для геймификации (достижения, миссии, онбординг)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime
import logging

from backend.core import get_db
from backend.models import (
    User, Achievement, UserAchievement, DailyMission, UserDailyMission,
    Transaction, LessonProgress
)
from backend.schemas import OnboardingSubmitRequest, BuyFreezeRequest, DailyMissionResponse

router = APIRouter(prefix="/api", tags=["gamification"])
logger = logging.getLogger(__name__)


@router.get("/achievements")
async def get_achievements(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить достижения пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserAchievement, Achievement)
        .join(Achievement)
        .where(UserAchievement.user_id == user.id)
    )
    user_achievements = result.all()

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
        "daily_missions": []
    }


@router.get("/daily-missions")
async def get_daily_missions(userId: str, db: AsyncSession = Depends(get_db)):
    """Ежедневные миссии"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.utcnow().date()
    result = await db.execute(
        select(DailyMission)
        .where(func.date(DailyMission.date) == today)
    )
    daily_missions = result.scalars().all()

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

        result = await db.execute(
            select(DailyMission)
            .where(func.date(DailyMission.date) == today)
        )
        daily_missions = result.scalars().all()

    missions_list = []
    for mission in daily_missions:
        result = await db.execute(
            select(UserDailyMission)
            .where(UserDailyMission.user_id == user.id)
            .where(UserDailyMission.mission_id == mission.id)
        )
        user_mission = result.scalar_one_or_none()

        if not user_mission:
            user_mission = UserDailyMission(
                user_id=user.id,
                mission_id=mission.id,
                progress=0,
                completed=False
            )
            db.add(user_mission)

        current_progress = 0
        if mission.mission_type == "transaction":
            result = await db.execute(
                select(func.count(Transaction.id))
                .where(Transaction.user_id == user.id)
                .where(func.date(Transaction.timestamp) == today)
            )
            current_progress = result.scalar() or 0

        elif mission.mission_type == "lesson":
            result = await db.execute(
                select(func.count(LessonProgress.id))
                .where(LessonProgress.user_id == user.id)
                .where(func.date(LessonProgress.completed_at) == today)
                .where(LessonProgress.completed == True)
            )
            current_progress = result.scalar() or 0

        elif mission.mission_type == "login":
            if user.last_activity and user.last_activity.date() == today:
                current_progress = 1

        user_mission.progress = current_progress
        if current_progress >= mission.target_value and not user_mission.completed:
            user_mission.completed = True
            user_mission.completed_at = datetime.utcnow()
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


@router.post("/buy-freeze")
async def buy_freeze(request: BuyFreezeRequest, db: AsyncSession = Depends(get_db)):
    """Покупка заморозки"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    freeze_cost = 500.0

    if user.current_balance < freeze_cost:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    user.current_balance -= freeze_cost
    user.streak += 1

    await db.commit()

    logger.info(f"User {user.username} bought freeze for {freeze_cost}")

    return {
        "success": True,
        "message": "Заморозка куплена! Ваша серия сохранена.",
        "new_balance": user.current_balance,
        "new_streak": user.streak
    }


@router.get("/onboarding/status")
async def get_onboarding_status(userId: str, db: AsyncSession = Depends(get_db)):
    """Проверить статус онбординга"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        return {"completed": False}

    return {"completed": user.onboarding_completed}


@router.get("/onboarding/questions")
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


@router.post("/onboarding/submit")
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


@router.get("/onboarding/result")
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


@router.get("/progress")
async def get_progress(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить прогресс пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(func.count(LessonProgress.id))
        .where(LessonProgress.user_id == user.id)
        .where(LessonProgress.completed == True)
    )
    completed_lessons = result.scalar() or 0

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


@router.get("/diary")
async def get_diary(userId: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Получить дневник активности"""
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


@router.get("/levels")
async def get_levels():
    """Получить информацию об уровнях"""
    return [
        {"level": i, "xp_required": 100, "title": f"Уровень {i}"}
        for i in range(1, 51)
    ]


@router.get("/recommendations")
async def get_recommendations(userId: str, db: AsyncSession = Depends(get_db)):
    """Рекомендации"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    recommendations = []

    if user.current_balance > 5000:
        recommendations.append({
            "type": "investment",
            "title": "Рассмотрите инвестиции",
            "description": f"У вас {user.current_balance:.0f} руб. Можно начать инвестировать в акции.",
            "action": "stocks"
        })

    if user.level < 5:
        recommendations.append({
            "type": "learning",
            "title": "Пройдите обучение",
            "description": "Изучите основы финансовой грамотности для повышения уровня.",
            "action": "learn"
        })

    if user.streak < 3:
        recommendations.append({
            "type": "activity",
            "title": "Поддерживайте активность",
            "description": "Заходите каждый день, чтобы увеличить серию.",
            "action": "daily"
        })

    return recommendations


@router.get("/experience")
async def get_experience(userId: str, db: AsyncSession = Depends(get_db)):
    """Опыт пользователя (legacy)"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"xp": user.xp, "level": user.level}


@router.post("/interactions")
async def post_interaction(userId: str, cardId: int, answer_index: int, db: AsyncSession = Depends(get_db)):
    """Взаимодействия (legacy)"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.xp += 5
    user.last_activity = datetime.utcnow()

    await db.commit()

    return {"success": True, "xp_earned": 5}
