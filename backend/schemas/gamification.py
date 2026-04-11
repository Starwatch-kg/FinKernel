"""
Pydantic схемы для геймификации
"""
from pydantic import BaseModel


class OnboardingSubmitRequest(BaseModel):
    userId: str
    answers: dict


class BuyFreezeRequest(BaseModel):
    userId: str


class DailyMissionResponse(BaseModel):
    id: int
    title: str
    description: str
    progress: int
    target: int
    xp_reward: int
    completed: bool
