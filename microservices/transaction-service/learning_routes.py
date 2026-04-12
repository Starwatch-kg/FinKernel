"""Learning System Routes"""

import sys
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from pydantic import BaseModel
from shared.db import get_db
from shared.models import Lesson, Module, User, UserProgress
from shared.redis import get_cache, publish_event, set_cache

router = APIRouter()


class CompleteLessonRequest(BaseModel):
    userId: str
    lessonId: int
    correctAnswers: int = 0
    totalQuestions: int = 0


# Seed data
MODULES_DATA = [
    {
        "id": 1,
        "title": "Основы финансов",
        "description": "Базовые концепции управления деньгами",
        "icon": "💰",
        "order": 1,
    },
    {
        "id": 2,
        "title": "Инвестиции",
        "description": "Как заставить деньги работать",
        "icon": "📈",
        "order": 2,
    },
    {
        "id": 3,
        "title": "Бюджетирование",
        "description": "Планирование расходов и доходов",
        "icon": "📊",
        "order": 3,
    },
    {
        "id": 4,
        "title": "Криптовалюты",
        "description": "Цифровые активы и блокчейн",
        "icon": "₿",
        "order": 4,
    },
]

LESSONS_DATA = [
    {
        "id": 1,
        "module_id": 1,
        "title": "Что такое бюджет?",
        "content": "Бюджет — это план доходов и расходов на определенный период. Он помогает контролировать финансы и достигать целей.",
        "duration_minutes": 5,
        "xp_reward": 10,
        "order": 1,
        "questions": [
            {
                "question": "Что такое бюджет?",
                "options": [
                    "План доходов и расходов",
                    "Список покупок",
                    "Банковский счет",
                    "Кредитная карта",
                ],
                "correct": 0,
                "explanation": "Бюджет — это структурированный план управления деньгами",
            }
        ],
    },
    {
        "id": 2,
        "module_id": 1,
        "title": "Правило 50/30/20",
        "content": "50% на необходимое, 30% на желаемое, 20% на сбережения. Это простая формула распределения дохода.",
        "duration_minutes": 7,
        "xp_reward": 15,
        "order": 2,
        "questions": [
            {
                "question": "Сколько процентов дохода нужно откладывать?",
                "options": ["10%", "20%", "30%", "50%"],
                "correct": 1,
                "explanation": "По правилу 50/30/20 на сбережения идет 20%",
            }
        ],
    },
    {
        "id": 3,
        "module_id": 2,
        "title": "Акции и облигации",
        "content": "Акции дают право на часть компании, облигации — это долговые бумаги. Акции рискованнее, но потенциально прибыльнее.",
        "duration_minutes": 10,
        "xp_reward": 20,
        "order": 1,
        "questions": [
            {
                "question": "Что безопаснее?",
                "options": ["Акции", "Облигации", "Криптовалюта", "Форекс"],
                "correct": 1,
                "explanation": "Облигации считаются более консервативным инструментом",
            }
        ],
    },
]


async def init_learning_data(db: AsyncSession):
    """Initialize modules and lessons"""
    for mod_data in MODULES_DATA:
        result = await db.execute(select(Module).where(Module.id == mod_data["id"]))
        if not result.scalar_one_or_none():
            module = Module(**mod_data)
            db.add(module)

    for lesson_data in LESSONS_DATA:
        result = await db.execute(select(Lesson).where(Lesson.id == lesson_data["id"]))
        if not result.scalar_one_or_none():
            lesson = Lesson(**lesson_data)
            db.add(lesson)

    await db.commit()


@router.get("/v2/modules")
async def get_modules(userId: str, db: AsyncSession = Depends(get_db)):
    await init_learning_data(db)

    user_id = int(userId) if userId.isdigit() else 1

    result = await db.execute(
        select(Module).where(Module.is_active == True).order_by(Module.order)
    )
    modules = result.scalars().all()

    modules_list = []
    for module in modules:
        # Count lessons
        lessons_result = await db.execute(
            select(func.count(Lesson.id)).where(
                Lesson.module_id == module.id, Lesson.is_active == True
            )
        )
        total_lessons = lessons_result.scalar()

        # Count completed lessons
        completed_result = await db.execute(
            select(func.count(UserProgress.id)).where(
                UserProgress.user_id == user_id,
                UserProgress.completed == True,
                UserProgress.lesson_id.in_(
                    select(Lesson.id).where(Lesson.module_id == module.id)
                ),
            )
        )
        completed_lessons = completed_result.scalar()

        modules_list.append(
            {
                "id": module.id,
                "title": module.title,
                "description": module.description,
                "icon": module.icon,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "progress": (
                    (completed_lessons / total_lessons * 100)
                    if total_lessons > 0
                    else 0
                ),
            }
        )

    return modules_list


@router.get("/v2/lessons")
async def get_module_lessons(
    userId: str, moduleId: int, db: AsyncSession = Depends(get_db)
):
    user_id = int(userId) if userId.isdigit() else 1

    result = await db.execute(
        select(Lesson)
        .where(Lesson.module_id == moduleId, Lesson.is_active == True)
        .order_by(Lesson.order)
    )
    lessons = result.scalars().all()

    lessons_list = []
    for lesson in lessons:
        # Check if completed
        progress_result = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user_id, UserProgress.lesson_id == lesson.id
            )
        )
        progress = progress_result.scalar_one_or_none()

        lessons_list.append(
            {
                "id": lesson.id,
                "title": lesson.title,
                "duration_minutes": lesson.duration_minutes,
                "xp_reward": lesson.xp_reward,
                "completed": progress.completed if progress else False,
                "score": progress.score if progress else None,
            }
        )

    return lessons_list


@router.get("/v2/lesson/{lesson_id}")
async def get_lesson_detail(
    lesson_id: int, userId: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(404, "Lesson not found")

    return {
        "id": lesson.id,
        "title": lesson.title,
        "content": lesson.content,
        "duration_minutes": lesson.duration_minutes,
        "xp_reward": lesson.xp_reward,
        "questions": lesson.questions or [],
    }


@router.post("/v2/complete-lesson")
async def complete_lesson(
    req: CompleteLessonRequest, db: AsyncSession = Depends(get_db)
):
    user_id = int(req.userId) if req.userId.isdigit() else 1

    # Check if lesson exists
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == req.lessonId))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    # Get or create progress
    progress_result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user_id, UserProgress.lesson_id == req.lessonId
        )
    )
    progress = progress_result.scalar_one_or_none()

    score = (
        int((req.correctAnswers / req.totalQuestions * 100))
        if req.totalQuestions > 0
        else 100
    )

    if progress:
        progress.completed = True
        progress.score = max(progress.score or 0, score)
        progress.completed_at = datetime.utcnow()
    else:
        progress = UserProgress(
            user_id=user_id,
            lesson_id=req.lessonId,
            completed=True,
            score=score,
            completed_at=datetime.utcnow(),
        )
        db.add(progress)

    # Award XP to user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        # Assuming User model has xp field (will add if needed)
        pass

    await db.commit()

    await publish_event(
        "lesson.completed",
        {
            "user_id": user_id,
            "lesson_id": req.lessonId,
            "score": score,
            "xp_earned": lesson.xp_reward,
        },
    )

    return {
        "status": "completed",
        "lesson_id": req.lessonId,
        "score": score,
        "xp_earned": lesson.xp_reward,
    }


@router.post("/v2/generate-lesson")
async def generate_lesson(
    userId: str,
    weakTopic: str = None,
    strongTopic: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered adaptive lesson"""
    # This will use OpenRouter in AI service
    from openrouter_client import OpenRouterClient

    client = OpenRouterClient()

    user_context = {"weak_topic": weakTopic, "strong_topic": strongTopic}

    topic = weakTopic or "financial basics"

    lesson_content = await client.generate_lesson_content(
        topic=topic, difficulty="medium", user_context=user_context
    )

    if not lesson_content:
        # Fallback
        lesson_content = {
            "title": f"Урок: {topic}",
            "content": "Это адаптивный урок, созданный специально для вас на основе ваших знаний.",
            "key_points": [
                "Основные концепции",
                "Практические примеры",
                "Применение в жизни",
            ],
            "questions": [
                {
                    "question": "Вопрос по теме",
                    "options": ["A", "B", "C", "D"],
                    "correct": 0,
                    "explanation": "Объяснение",
                }
            ],
        }

    return lesson_content
