"""Adaptive AI System Routes"""

import json
import sys
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from pydantic import BaseModel
from shared.db import get_db
from shared.models import AdaptiveAnswer, AdaptiveProfile, User
from shared.redis import get_cache, publish_event, set_cache

router = APIRouter()


class RecordAnswerRequest(BaseModel):
    userId: str
    topic: str
    questionId: str
    isCorrect: bool
    timeMs: int = 0
    source: str = "lesson"


TOPICS = [
    "budgeting",
    "investing",
    "savings",
    "debt_management",
    "retirement",
    "taxes",
    "insurance",
    "real_estate",
    "stocks",
    "crypto",
]


async def get_or_create_profile(user_id: int, db: AsyncSession) -> AdaptiveProfile:
    """Get or create adaptive profile for user"""
    result = await db.execute(
        select(AdaptiveProfile).where(AdaptiveProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        initial_mastery = {topic: 0.5 for topic in TOPICS}
        profile = AdaptiveProfile(
            user_id=user_id,
            mastery_scores=initial_mastery,
            learning_velocity=1.0,
            preferred_difficulty="medium",
            weak_topics=[],
            strong_topics=[],
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


@router.get("/adaptive/mastery")
async def get_mastery(userId: str, db: AsyncSession = Depends(get_db)):
    """Get user's mastery scores across all topics"""
    user_id = int(userId) if userId.isdigit() else 1

    profile = await get_or_create_profile(user_id, db)

    mastery_data = []
    for topic, score in profile.mastery_scores.items():
        mastery_data.append(
            {
                "topic": topic,
                "score": round(score, 2),
                "level": (
                    "beginner"
                    if score < 0.4
                    else "intermediate" if score < 0.7 else "advanced"
                ),
            }
        )

    return {
        "user_id": user_id,
        "mastery": mastery_data,
        "overall_score": round(
            sum(profile.mastery_scores.values()) / len(profile.mastery_scores), 2
        ),
        "learning_velocity": profile.learning_velocity,
    }


@router.get("/adaptive/recommendation")
async def get_recommendation(userId: str, db: AsyncSession = Depends(get_db)):
    """Get personalized learning recommendation"""
    user_id = int(userId) if userId.isdigit() else 1

    profile = await get_or_create_profile(user_id, db)

    # Find weakest topic
    weak_topic = min(profile.mastery_scores.items(), key=lambda x: x[1])
    strong_topic = max(profile.mastery_scores.items(), key=lambda x: x[1])

    # Get recent performance
    recent_result = await db.execute(
        select(AdaptiveAnswer)
        .where(AdaptiveAnswer.user_id == user_id)
        .order_by(AdaptiveAnswer.created_at.desc())
        .limit(10)
    )
    recent_answers = recent_result.scalars().all()

    recent_accuracy = (
        sum(1 for a in recent_answers if a.is_correct) / len(recent_answers)
        if recent_answers
        else 0.5
    )

    recommendation = {
        "recommended_topic": weak_topic[0],
        "current_mastery": round(weak_topic[1], 2),
        "difficulty": (
            "easy"
            if weak_topic[1] < 0.3
            else "medium" if weak_topic[1] < 0.6 else "hard"
        ),
        "reason": f"Focus on {weak_topic[0]} to improve overall mastery",
        "estimated_time_minutes": 15,
        "recent_accuracy": round(recent_accuracy, 2),
        "strong_topic": strong_topic[0],
    }

    return recommendation


@router.get("/adaptive/next-question")
async def get_next_question(
    topic: str, userId: str, db: AsyncSession = Depends(get_db)
):
    """Get next adaptive question for topic"""
    user_id = int(userId) if userId.isdigit() else 1

    profile = await get_or_create_profile(user_id, db)

    mastery = profile.mastery_scores.get(topic, 0.5)

    # Determine difficulty based on mastery
    if mastery < 0.4:
        difficulty = "easy"
    elif mastery < 0.7:
        difficulty = "medium"
    else:
        difficulty = "hard"

    # Generate question using OpenRouter
    from openrouter_client import OpenRouterClient

    client = OpenRouterClient()

    question = await client.generate_adaptive_question(topic, difficulty, mastery)

    if not question:
        # Fallback question
        question = {
            "question": f"Question about {topic}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct": 0,
            "explanation": "This is the correct answer because...",
            "difficulty_score": mastery,
        }

    question["id"] = f"{topic}_{int(datetime.utcnow().timestamp())}"
    question["topic"] = topic

    return question


@router.get("/adaptive/lesson-questions")
async def get_lesson_questions(
    topic: str, count: int = 3, userId: str = "1", db: AsyncSession = Depends(get_db)
):
    """Get multiple questions for a lesson"""
    user_id = int(userId) if userId.isdigit() else 1

    questions = []
    for i in range(count):
        question = await get_next_question(topic, userId, db)
        questions.append(question)

    return questions


@router.post("/adaptive/answer")
async def record_answer(req: RecordAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Record user answer and update mastery"""
    user_id = int(req.userId) if req.userId.isdigit() else 1

    # Record answer
    answer = AdaptiveAnswer(
        user_id=user_id,
        topic=req.topic,
        question_id=req.questionId,
        is_correct=req.isCorrect,
        time_ms=req.timeMs,
        source=req.source,
    )
    db.add(answer)

    # Update profile
    profile = await get_or_create_profile(user_id, db)

    # Update mastery score using exponential moving average
    current_mastery = profile.mastery_scores.get(req.topic, 0.5)
    learning_rate = 0.1

    if req.isCorrect:
        new_mastery = current_mastery + learning_rate * (1.0 - current_mastery)
    else:
        new_mastery = current_mastery - learning_rate * current_mastery

    new_mastery = max(0.0, min(1.0, new_mastery))

    mastery_scores = profile.mastery_scores.copy()
    mastery_scores[req.topic] = new_mastery
    profile.mastery_scores = mastery_scores

    # Update stats
    profile.total_questions += 1
    if req.isCorrect:
        profile.correct_answers += 1

    # Update weak/strong topics
    sorted_topics = sorted(mastery_scores.items(), key=lambda x: x[1])
    profile.weak_topics = [t[0] for t in sorted_topics[:3]]
    profile.strong_topics = [t[0] for t in sorted_topics[-3:]]

    # Update learning velocity based on recent performance
    recent_result = await db.execute(
        select(AdaptiveAnswer).where(
            AdaptiveAnswer.user_id == user_id,
            AdaptiveAnswer.created_at >= datetime.utcnow() - timedelta(days=7),
        )
    )
    recent_answers = recent_result.scalars().all()

    if len(recent_answers) >= 10:
        recent_accuracy = sum(1 for a in recent_answers if a.is_correct) / len(
            recent_answers
        )
        profile.learning_velocity = 0.5 + recent_accuracy

    profile.updated_at = datetime.utcnow()

    await db.commit()

    await publish_event(
        "adaptive.answer_recorded",
        {
            "user_id": user_id,
            "topic": req.topic,
            "is_correct": req.isCorrect,
            "new_mastery": new_mastery,
        },
    )

    return {
        "status": "recorded",
        "new_mastery": round(new_mastery, 2),
        "mastery_change": round(new_mastery - current_mastery, 3),
        "total_accuracy": (
            round(profile.correct_answers / profile.total_questions, 2)
            if profile.total_questions > 0
            else 0
        ),
    }


@router.post("/adaptive/generate-question")
async def generate_question(
    userId: str, topic: str = None, db: AsyncSession = Depends(get_db)
):
    """Generate new question using AI"""
    user_id = int(userId) if userId.isdigit() else 1

    if not topic:
        # Get recommended topic
        recommendation = await get_recommendation(userId, db)
        topic = recommendation["recommended_topic"]

    return await get_next_question(topic, userId, db)
