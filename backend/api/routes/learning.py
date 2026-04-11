"""
Роутер для обучения (модули, уроки, адаптивное обучение)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import logging

from backend.core import get_db
from backend.models import (
    User, Module, Lesson, LessonProgress, AdaptiveMastery, AdaptiveQuestion
)
from backend.schemas import (
    CompleteLessonRequest,
    GenerateLessonRequest,
    GeneratedLessonResponse,
    AdaptiveAnswerRequest,
)
from backend.services import generate_lesson_with_llm, generate_adaptive_question_with_llm

router = APIRouter(prefix="/api", tags=["learning"])
logger = logging.getLogger(__name__)


@router.get("/v2/modules")
async def get_modules(userId: str, db: AsyncSession = Depends(get_db)):
    """Получить все модули обучения"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Module).order_by(Module.order))
    modules = result.scalars().all()

    modules_list = []
    for module in modules:
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


@router.get("/v2/lessons")
async def get_module_lessons(userId: str, moduleId: int, db: AsyncSession = Depends(get_db)):
    """Получить уроки модуля"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Lesson)
        .where(Lesson.module_id == moduleId)
        .order_by(Lesson.order)
    )
    lessons = result.scalars().all()

    lessons_list = []
    for lesson in lessons:
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


@router.get("/v2/lesson/{lessonId}")
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


@router.post("/v2/complete-lesson")
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

    user.xp += lesson.xp_reward
    user.last_activity = datetime.utcnow()

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


@router.post("/v2/generate-lesson", response_model=GeneratedLessonResponse)
async def generate_lesson(request: GenerateLessonRequest, db: AsyncSession = Depends(get_db)):
    """Генерация урока через LLM с fallback"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        lesson_data = await generate_lesson_with_llm(request.weakTopic, request.strongTopic)
        logger.info(f"Generated lesson for user {user.username}: {lesson_data['title']}")

        return GeneratedLessonResponse(
            title=lesson_data["title"],
            content=lesson_data["content"],
            questions=lesson_data["questions"],
            xp_reward=lesson_data["xp_reward"]
        )

    except Exception as e:
        logger.error(f"Error generating lesson: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate lesson")


@router.get("/adaptive/mastery")
async def get_adaptive_mastery(userId: str, db: AsyncSession = Depends(get_db)):
    """Адаптивное обучение - мастерство"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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


@router.get("/adaptive/recommendation")
async def get_adaptive_recommendation(userId: str, db: AsyncSession = Depends(get_db)):
    """Адаптивные рекомендации"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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


@router.get("/adaptive/next-question")
async def get_adaptive_next_question(topic: str, userId: str, db: AsyncSession = Depends(get_db)):
    """Следующий вопрос"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(AdaptiveMastery)
        .where(AdaptiveMastery.user_id == user.id)
        .where(AdaptiveMastery.topic == topic)
    )
    mastery = result.scalar_one_or_none()

    if mastery:
        difficulty = min(0.9, mastery.mastery_level + 0.1)
    else:
        difficulty = 0.3

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


@router.get("/adaptive/lesson-questions")
async def get_adaptive_lesson_questions(topic: str, count: int, userId: str, db: AsyncSession = Depends(get_db)):
    """Вопросы урока"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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


@router.post("/adaptive/answer")
async def record_adaptive_answer(request: AdaptiveAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Записать ответ"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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

    mastery.total_answers += 1
    if request.isCorrect:
        mastery.correct_answers += 1

    mastery.mastery_level = mastery.correct_answers / mastery.total_answers if mastery.total_answers > 0 else 0.0
    mastery.last_practiced = datetime.utcnow()

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


@router.get("/adaptive/generate-question")
async def generate_question(userId: str, topic: str = None, db: AsyncSession = Depends(get_db)):
    """Генерация вопроса через LLM с fallback"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not topic:
        result = await db.execute(
            select(AdaptiveMastery)
            .where(AdaptiveMastery.user_id == user.id)
            .order_by(AdaptiveMastery.mastery_level)
            .limit(1)
        )
        mastery = result.scalar_one_or_none()
        topic = mastery.topic if mastery else "Основы финансов"

    result = await db.execute(
        select(AdaptiveMastery)
        .where(AdaptiveMastery.user_id == user.id)
        .where(AdaptiveMastery.topic == topic)
    )
    mastery = result.scalar_one_or_none()

    difficulty = mastery.mastery_level + 0.1 if mastery else 0.3

    try:
        question_data = await generate_adaptive_question_with_llm(topic, difficulty)

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
