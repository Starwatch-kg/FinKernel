"""Market Events and Gamification Routes"""

import sys
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from pydantic import BaseModel
from shared.db import get_db
from shared.logger import setup_logger
from shared.models import (
    Achievement,
    DailyMission,
    MarketEvent,
    Transaction,
    User,
    UserMarketResponse,
)
from shared.redis import get_cache, publish_event, set_cache

logger = setup_logger("market_events")
router = APIRouter()


class MarketActionRequest(BaseModel):
    userId: str
    eventId: int
    action: str


# Market event templates
EVENT_TEMPLATES = [
    {
        "title": "Процентная ставка ФРС выросла",
        "description": "Федеральная резервная система США повысила ставку на 0.25%. Как это повлияет на рынок?",
        "impact": "negative",
        "options": [
            "Продать акции",
            "Купить облигации",
            "Держать позиции",
            "Купить золото",
        ],
        "correct_option": 1,
    },
    {
        "title": "Tech-гигант представил новый продукт",
        "description": "Apple анонсировала революционное устройство. Акции выросли на 5%.",
        "impact": "positive",
        "options": ["Купить акции", "Продать акции", "Ждать коррекции", "Игнорировать"],
        "correct_option": 0,
    },
    {
        "title": "Геополитическая напряженность",
        "description": "Конфликт на Ближнем Востоке усилился. Цены на нефть растут.",
        "impact": "mixed",
        "options": [
            "Купить нефтяные акции",
            "Продать все",
            "Диверсифицировать",
            "Купить защитные активы",
        ],
        "correct_option": 3,
    },
]


async def init_market_events(db: AsyncSession):
    """Create active market events if none exist - uses deterministic selection"""
    result = await db.execute(
        select(MarketEvent).where(
            MarketEvent.is_active == True, MarketEvent.expires_at > datetime.utcnow()
        )
    )
    active_events = result.scalars().all()

    if len(active_events) < 2:
        # Create new events - deterministic selection based on day of year
        day_of_year = datetime.utcnow().timetuple().tm_yday
        template_index = day_of_year % len(EVENT_TEMPLATES)
        template = EVENT_TEMPLATES[template_index]

        event = MarketEvent(
            title=template["title"],
            description=template["description"],
            impact=template["impact"],
            options=template["options"],
            correct_option=template["correct_option"],
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=True,
        )
        db.add(event)
        logger.info(f"Created market event: {template['title']}")
        await db.commit()


@router.get("/market-event")
async def get_market_event(userId: str, db: AsyncSession = Depends(get_db)):
    """Get current active market event"""
    user_id = int(userId) if userId.isdigit() else 1

    await init_market_events(db)

    # Get event user hasn't responded to
    result = await db.execute(
        select(MarketEvent)
        .where(
            MarketEvent.is_active == True,
            MarketEvent.expires_at > datetime.utcnow(),
            ~MarketEvent.id.in_(
                select(UserMarketResponse.event_id).where(
                    UserMarketResponse.user_id == user_id
                )
            ),
        )
        .limit(1)
    )
    event = result.scalar_one_or_none()

    if not event:
        return None

    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "impact": event.impact,
        "options": event.options,
        "expires_at": event.expires_at.isoformat(),
    }


@router.post("/market-event/action")
async def market_event_action(
    req: MarketActionRequest, db: AsyncSession = Depends(get_db)
):
    """Record user's response to market event"""
    user_id = int(req.userId) if req.userId.isdigit() else 1

    # Get event
    event_result = await db.execute(
        select(MarketEvent).where(MarketEvent.id == req.eventId)
    )
    event = event_result.scalar_one_or_none()

    if not event:
        raise HTTPException(404, "Event not found")

    # Check if already responded
    response_result = await db.execute(
        select(UserMarketResponse).where(
            UserMarketResponse.user_id == user_id,
            UserMarketResponse.event_id == req.eventId,
        )
    )
    existing = response_result.scalar_one_or_none()

    if existing:
        raise HTTPException(400, "Already responded to this event")

    # Determine if correct
    is_correct = (
        event.options.index(req.action) == event.correct_option
        if req.action in event.options
        else False
    )
    xp_earned = 15 if is_correct else 5

    # Record response
    response = UserMarketResponse(
        user_id=user_id,
        event_id=req.eventId,
        action=req.action,
        is_correct=is_correct,
        xp_earned=xp_earned,
    )
    db.add(response)
    await db.commit()

    await publish_event(
        "market.event_responded",
        {
            "user_id": user_id,
            "event_id": req.eventId,
            "is_correct": is_correct,
            "xp_earned": xp_earned,
        },
    )

    return {
        "status": "recorded",
        "is_correct": is_correct,
        "xp_earned": xp_earned,
        "correct_action": event.options[event.correct_option],
    }


ACHIEVEMENT_TEMPLATES = [
    # Экономия (savings)
    {"id": 1, "name": "Первая экономия", "description": "Сэкономь 1000с", "icon": "💰", "category": "savings", "xp_reward": 50},
    {"id": 2, "name": "Бережливый", "description": "Сэкономь 5000с", "icon": "🏦", "category": "savings", "xp_reward": 100},
    {"id": 3, "name": "Мастер экономии", "description": "Сэкономь 10000с", "icon": "💎", "category": "savings", "xp_reward": 200},
    {"id": 4, "name": "Финансовый гений", "description": "Сэкономь 50000с", "icon": "👑", "category": "savings", "xp_reward": 500},
    {"id": 5, "name": "Миллионер", "description": "Накопи 1000000с", "icon": "🎯", "category": "savings", "xp_reward": 1000},

    # Бюджет (budget)
    {"id": 6, "name": "Первый бюджет", "description": "Создай свой первый бюджет", "icon": "📊", "category": "budget", "xp_reward": 50},
    {"id": 7, "name": "Планировщик", "description": "Соблюдай бюджет 7 дней подряд", "icon": "📅", "category": "budget", "xp_reward": 100},
    {"id": 8, "name": "Бюджетный мастер", "description": "Соблюдай бюджет месяц", "icon": "🎓", "category": "budget", "xp_reward": 300},
    {"id": 9, "name": "Финансовый контроль", "description": "Не превысь бюджет 3 месяца", "icon": "🛡️", "category": "budget", "xp_reward": 500},
    {"id": 10, "name": "Идеальный баланс", "description": "Соблюдай бюджет полгода", "icon": "⚖️", "category": "budget", "xp_reward": 800},

    # Дисциплина (discipline)
    {"id": 11, "name": "Первый шаг", "description": "Добавь первую транзакцию", "icon": "✨", "category": "discipline", "xp_reward": 25},
    {"id": 12, "name": "Активный пользователь", "description": "Добавь 10 транзакций", "icon": "📝", "category": "discipline", "xp_reward": 75},
    {"id": 13, "name": "Записывающий всё", "description": "Добавь 50 транзакций", "icon": "📚", "category": "discipline", "xp_reward": 150},
    {"id": 14, "name": "Финансовый аналитик", "description": "Добавь 100 транзакций", "icon": "📈", "category": "discipline", "xp_reward": 300},
    {"id": 15, "name": "Мастер учёта", "description": "Добавь 500 транзакций", "icon": "🏆", "category": "discipline", "xp_reward": 750},

    # Серия (streak)
    {"id": 16, "name": "Начало пути", "description": "Используй приложение 3 дня подряд", "icon": "🔥", "category": "streak", "xp_reward": 50},
    {"id": 17, "name": "Неделя силы", "description": "Используй приложение 7 дней подряд", "icon": "💪", "category": "streak", "xp_reward": 100},
    {"id": 18, "name": "Двухнедельный марафон", "description": "Используй приложение 14 дней подряд", "icon": "🎖️", "category": "streak", "xp_reward": 200},
    {"id": 19, "name": "Месяц дисциплины", "description": "Используй приложение 30 дней подряд", "icon": "🌟", "category": "streak", "xp_reward": 400},
    {"id": 20, "name": "Легенда", "description": "Используй приложение 100 дней подряд", "icon": "👑", "category": "streak", "xp_reward": 1000},

    # Обучение
    {"id": 21, "name": "Ученик", "description": "Пройди первый урок", "icon": "🎓", "category": "discipline", "xp_reward": 50},
    {"id": 22, "name": "Знаток", "description": "Пройди 5 уроков", "icon": "📖", "category": "discipline", "xp_reward": 150},
    {"id": 23, "name": "Эксперт", "description": "Пройди все уроки", "icon": "🧠", "category": "discipline", "xp_reward": 500},

    # Категории расходов
    {"id": 24, "name": "Категоризатор", "description": "Используй 5 разных категорий", "icon": "🏷️", "category": "discipline", "xp_reward": 100},
    {"id": 25, "name": "Организатор", "description": "Используй все категории", "icon": "🗂️", "category": "discipline", "xp_reward": 200},

    # Цели
    {"id": 26, "name": "Целеустремлённый", "description": "Создай первую финансовую цель", "icon": "🎯", "category": "savings", "xp_reward": 75},
    {"id": 27, "name": "Достигатор", "description": "Достигни первой цели", "icon": "🏅", "category": "savings", "xp_reward": 200},
    {"id": 28, "name": "Мечтатель", "description": "Достигни 5 целей", "icon": "🌈", "category": "savings", "xp_reward": 500},

    # Особые
    {"id": 29, "name": "Ранняя пташка", "description": "Войди в приложение до 7 утра", "icon": "🌅", "category": "streak", "xp_reward": 100},
    {"id": 30, "name": "Полуночник", "description": "Добавь транзакцию после полуночи", "icon": "🌙", "category": "streak", "xp_reward": 100},
]


async def get_generated_achievement_templates(
    user_id: int, db: AsyncSession
) -> list[dict]:
    """Generate a few personalized achievements from current user activity."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
    )
    transactions = result.scalars().all()

    income_count = sum(1 for txn in transactions if txn.type.value == "income")
    described_count = sum(1 for txn in transactions if (txn.description or "").strip())
    active_days = len({txn.timestamp.date().isoformat() for txn in transactions})

    return [
        {
            "id": 101,
            "name": "История доходов",
            "description": "AI-цель: добавь 3 доходные транзакции",
            "icon": "🤖",
            "category": "budget",
            "xp_reward": 80,
            "generated": True,
            "unlocked": income_count >= 3,
        },
        {
            "id": 102,
            "name": "Финансовый дневник",
            "description": "AI-цель: оставь комментарий к 5 транзакциям",
            "icon": "🧠",
            "category": "discipline",
            "xp_reward": 90,
            "generated": True,
            "unlocked": described_count >= 5,
        },
        {
            "id": 103,
            "name": "Ритм недели",
            "description": "AI-цель: веди учёт расходов 7 разных дней",
            "icon": "📆",
            "category": "streak",
            "xp_reward": 120,
            "generated": True,
            "unlocked": active_days >= 7,
        },
    ]

@router.get("/achievements")
async def get_achievements(userId: str, db: AsyncSession = Depends(get_db)):
    """Get user achievements"""
    user_id = int(userId) if userId.isdigit() else 1

    result = await db.execute(
        select(Achievement)
        .where(Achievement.user_id == user_id)
        .order_by(Achievement.unlocked_at.desc())
    )
    unlocked = result.scalars().all()
    unlocked_ids = {a.title for a in unlocked}

    generated_templates = await get_generated_achievement_templates(user_id, db)
    all_templates = ACHIEVEMENT_TEMPLATES + generated_templates

    # Return all achievements with unlocked status
    achievements_list = []
    for template in all_templates:
        unlocked_ach = next((a for a in unlocked if a.title == template["name"]), None)
        achievements_list.append({
            "id": template["id"],
            "name": template["name"],
            "description": template["description"],
            "icon": template["icon"],
            "category": template["category"],
            "xp_reward": template["xp_reward"],
            "generated": template.get("generated", False),
            "unlocked": template.get("unlocked", template["name"] in unlocked_ids),
            "unlocked_at": unlocked_ach.unlocked_at.isoformat() if unlocked_ach else None,
        })

    return achievements_list


@router.get("/daily-missions")
async def get_daily_missions(userId: str, db: AsyncSession = Depends(get_db)):
    """Get daily missions for user"""
    user_id = int(userId) if userId.isdigit() else 1

    today = datetime.utcnow().date()

    # Get today's missions
    result = await db.execute(
        select(DailyMission).where(
            DailyMission.user_id == user_id, func.date(DailyMission.date) == today
        )
    )
    missions = result.scalars().all()

    # Create missions if none exist
    if not missions:
        mission_templates = [
            {
                "title": "Добавь 3 транзакции",
                "description": "Запиши свои расходы",
                "target": 3,
            },
            {"title": "Пройди 1 урок", "description": "Изучи новую тему", "target": 1},
            {
                "title": "Проверь портфель",
                "description": "Посмотри на свои инвестиции",
                "target": 1,
            },
        ]

        for template in mission_templates:
            mission = DailyMission(
                user_id=user_id,
                title=template["title"],
                description=template["description"],
                progress=0,
                target=template["target"],
                xp_reward=10,
                completed=False,
                date=datetime.utcnow(),
            )
            db.add(mission)
            missions.append(mission)

        await db.commit()

    return [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "progress": m.progress,
            "target": m.target,
            "xp_reward": m.xp_reward,
            "completed": m.completed,
        }
        for m in missions
    ]


@router.get("/progress")
async def get_progress(userId: str, db: AsyncSession = Depends(get_db)):
    """Get user progress and level"""
    user_id = int(userId) if userId.isdigit() else 1

    # Calculate XP from various sources
    achievements_result = await db.execute(
        select(func.sum(Achievement.xp_reward)).where(Achievement.user_id == user_id)
    )
    achievements_xp = achievements_result.scalar() or 0

    missions_result = await db.execute(
        select(func.sum(DailyMission.xp_reward)).where(
            DailyMission.user_id == user_id, DailyMission.completed == True
        )
    )
    missions_xp = missions_result.scalar() or 0

    total_xp = int(achievements_xp + missions_xp)

    # Calculate level (100 XP per level)
    level = total_xp // 100 + 1
    current_level_xp = total_xp % 100
    next_level_xp = 100

    return {
        "level": level,
        "xp": current_level_xp,
        "total_xp": total_xp,
        "next_level_xp": next_level_xp,
        "progress_percent": (current_level_xp / next_level_xp * 100),
    }


@router.get("/levels")
async def get_levels():
    """Get level definitions"""
    levels = []
    for i in range(1, 51):
        levels.append(
            {"level": i, "xp_required": i * 100, "title": f"Level {i}", "rewards": []}
        )
    return levels


@router.get("/diary")
async def get_diary(userId: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get user diary entries"""
    user_id = int(userId) if userId.isdigit() else 1

    from shared.models import DiaryEntry

    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.user_id == user_id)
        .order_by(DiaryEntry.created_at.desc())
        .limit(limit)
    )
    entries = result.scalars().all()

    return [
        {
            "id": e.id,
            "content": e.content,
            "mood": e.mood,
            "tags": e.tags,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@router.get("/experience")
async def get_experience(userId: str, db: AsyncSession = Depends(get_db)):
    """Get user experience summary"""
    progress = await get_progress(userId, db)
    return progress


@router.post("/interactions")
async def post_interaction(data: dict, db: AsyncSession = Depends(get_db)):
    """Record user interaction (legacy endpoint)"""
    user_id = int(data.get("userId", 1))

    # Just acknowledge
    return {"status": "recorded", "xp_earned": 5}


@router.post("/buy-freeze")
async def buy_freeze(data: dict, db: AsyncSession = Depends(get_db)):
    """Buy spending freeze power-up"""
    user_id = int(data.get("userId", 1))

    freeze_cost = 100

    async with db.begin():
        # Lock user row to prevent concurrent balance modifications
        user_result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not found")

        # Check balance INSIDE lock
        if user.balance < freeze_cost:
            raise HTTPException(400, "Insufficient funds")

        user.balance -= freeze_cost
        await db.flush()

    return {"status": "purchased", "cost": freeze_cost, "new_balance": user.balance}
