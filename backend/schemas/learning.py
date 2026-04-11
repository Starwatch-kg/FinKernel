"""
Pydantic схемы для обучения
"""
from pydantic import BaseModel
from typing import List, Optional


class CompleteLessonRequest(BaseModel):
    userId: str
    lessonId: int
    correctAnswers: int = 0
    totalQuestions: int = 0


class GenerateLessonRequest(BaseModel):
    userId: str
    weakTopic: Optional[str] = None
    strongTopic: Optional[str] = None


class GeneratedLessonResponse(BaseModel):
    title: str
    content: str
    questions: List[dict]
    xp_reward: int


class AdaptiveAnswerRequest(BaseModel):
    userId: str
    topic: str
    questionId: int
    isCorrect: bool
    timeMs: int = 0
    source: str = "lesson"
