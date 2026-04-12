"""AI Output Validation and Hardening"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator
from shared.logger import setup_logger

logger = setup_logger("ai_validation")


class RiskLevel(str, Enum):
    """Valid risk levels"""

    safe = "safe"
    warning = "warning"
    danger = "danger"
    critical = "critical"


class ValidatedPrediction(BaseModel):
    """Strict schema for AI predictions"""

    days_left: Optional[float] = Field(None, ge=0, le=365)
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommendation: str = Field(..., min_length=10, max_length=500)
    ai_used: bool = Field(default=False)

    @validator("days_left")
    def validate_days_left(cls, v):
        if v is not None and (v < 0 or v > 365):
            raise ValueError("days_left must be between 0 and 365")
        return v

    @validator("recommendation")
    def validate_recommendation(cls, v):
        # Check for prompt injection patterns
        dangerous_patterns = [
            "ignore previous",
            "disregard",
            "system:",
            "assistant:",
            "<script>",
            "javascript:",
            "eval(",
            "exec(",
        ]

        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                logger.warning(f"Rejected AI output with dangerous pattern: {pattern}")
                raise ValueError("Invalid recommendation content")

        return v


class ValidatedQuestion(BaseModel):
    """Strict schema for AI-generated questions"""

    question: str = Field(..., min_length=10, max_length=500)
    options: list[str] = Field(..., min_items=2, max_items=4)
    correct_answer: int = Field(..., ge=0, le=3)
    explanation: str = Field(..., min_length=10, max_length=1000)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    topic: str = Field(..., min_length=2, max_length=100)

    @validator("options")
    def validate_options(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("Options must be unique")

        for option in v:
            if len(option) < 1 or len(option) > 200:
                raise ValueError("Each option must be 1-200 characters")

        return v

    @validator("correct_answer")
    def validate_correct_answer(cls, v, values):
        if "options" in values and v >= len(values["options"]):
            raise ValueError("correct_answer index out of range")
        return v


class AIValidator:
    """Validate AI outputs with confidence thresholds"""

    MIN_CONFIDENCE_THRESHOLD = 0.6
    MIN_CONFIDENCE_FOR_CRITICAL = 0.8

    @staticmethod
    def validate_prediction(
        raw_output: Dict[str, Any], min_confidence: Optional[float] = None
    ) -> ValidatedPrediction:
        """Validate and sanitize AI prediction output"""
        try:
            prediction = ValidatedPrediction(**raw_output)

            # Check confidence threshold
            threshold = min_confidence or AIValidator.MIN_CONFIDENCE_THRESHOLD
            if prediction.confidence < threshold:
                logger.warning(
                    f"AI prediction below confidence threshold: {prediction.confidence} < {threshold}"
                )
                raise ValueError(f"Confidence too low: {prediction.confidence}")

            # Extra validation for critical risk
            if prediction.risk_level == RiskLevel.critical:
                if prediction.confidence < AIValidator.MIN_CONFIDENCE_FOR_CRITICAL:
                    logger.warning(
                        f"Critical risk prediction with low confidence: {prediction.confidence}"
                    )
                    raise ValueError("Critical predictions require higher confidence")

            return prediction

        except Exception as e:
            logger.error(f"AI prediction validation failed: {e}")
            raise

    @staticmethod
    def validate_question(raw_output: Dict[str, Any]) -> ValidatedQuestion:
        """Validate AI-generated question"""
        try:
            question = ValidatedQuestion(**raw_output)
            return question
        except Exception as e:
            logger.error(f"AI question validation failed: {e}")
            raise

    @staticmethod
    def sanitize_ai_text(text: str, max_length: int = 1000) -> str:
        """Sanitize AI-generated text"""
        # Remove potential injection patterns
        text = text.replace("<", "&lt;").replace(">", "&gt;")

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text.strip()

    @staticmethod
    def create_safe_fallback_prediction(
        balance: float, avg_daily_expense: float
    ) -> ValidatedPrediction:
        """Create safe fallback prediction when AI fails"""
        if avg_daily_expense <= 0:
            days_left = None
            risk_level = RiskLevel.safe
            recommendation = (
                "Недостаточно данных для прогноза. Продолжайте отслеживать расходы."
            )
        else:
            days_left = balance / avg_daily_expense if balance > 0 else 0

            if days_left > 30:
                risk_level = RiskLevel.safe
                recommendation = (
                    "Ваш бюджет в безопасности. Продолжайте контролировать расходы."
                )
            elif days_left > 14:
                risk_level = RiskLevel.warning
                recommendation = (
                    "Следите за расходами. Рекомендуем сократить необязательные траты."
                )
            elif days_left > 7:
                risk_level = RiskLevel.danger
                recommendation = (
                    "Внимание! Средства заканчиваются. Срочно сократите расходы."
                )
            else:
                risk_level = RiskLevel.critical
                recommendation = "Критическая ситуация! Немедленно пересмотрите бюджет."

        return ValidatedPrediction(
            days_left=days_left,
            risk_level=risk_level,
            confidence=0.7,
            recommendation=recommendation,
            ai_used=False,
        )
