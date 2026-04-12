"""
SECURE PREDICTION ENGINE - Prompt injection protection
"""

import json
import re
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.append("/app")

from shared.logger import setup_logger
from shared.security_hardening import sanitize_for_llm

logger = setup_logger("prediction_engine_secure")


class PredictionEngine:
    def __init__(self):
        self.min_txns = 3

        # Primary: Groq
        self.groq = None
        try:
            from groq_client import GroqClient
            self.groq = GroqClient()
            if not self.groq.client:
                self.groq = None
        except ImportError:
            logger.warning("Groq client not available")

        # Fallback: OpenRouter
        self.openrouter = None
        try:
            from openrouter_client_secure import OpenRouterClient
            self.openrouter = OpenRouterClient()
            if not self.openrouter.client:
                self.openrouter = None
        except ImportError:
            logger.warning("OpenRouter client not available")

        providers = []
        if self.groq:
            providers.append("Groq")
        if self.openrouter:
            providers.append("OpenRouter")
        providers.append("Statistical")
        logger.info(f"LLM cascade: {' → '.join(providers)}")

    def calculate_features(self, transactions: List[Dict]) -> Dict:
        """Calculate statistical features from transactions"""
        if not transactions:
            return self._default_features()

        expenses = [t["amount"] for t in transactions if t["type"] == "expense"]
        if not expenses:
            return self._default_features()

        arr = np.array(expenses)
        daily_avg = np.mean(arr)
        rolling_7d = np.mean(arr[-7:]) if len(arr) >= 7 else daily_avg
        rolling_30d = np.mean(arr[-30:]) if len(arr) >= 30 else daily_avg
        volatility = np.std(arr) if len(arr) > 1 else 0.0
        trend_slope = self._calc_trend(arr)

        return {
            "daily_avg": float(daily_avg),
            "rolling_7d": float(rolling_7d),
            "rolling_30d": float(rolling_30d),
            "volatility": float(volatility),
            "trend_slope": float(trend_slope),
            "total_txns": len(expenses),
        }

    async def predict(
        self, balance: float, features: Dict, transactions: List[Dict]
    ) -> Tuple[Optional[float], float, str, str, bool]:
        """
        Cascading prediction: Groq → OpenRouter → Statistical.
        Returns (days_left, confidence, risk_level, recommendation, ai_used)
        """
        if features["total_txns"] < self.min_txns:
            return None, 0.3, "safe", "📊 Недостаточно данных", False

        if balance <= 0:
            return 0, 0.95, "critical", "⚠️ Баланс на нуле!", False

        # 1. Try Groq (primary)
        if self.groq:
            try:
                result = await self.groq.predict_financial_runway(
                    balance, transactions, features
                )
                if result and self._validate_llm_output(result):
                    logger.info("✅ Prediction via Groq")
                    return (
                        result["days_left"],
                        result["confidence"],
                        result["risk_level"],
                        result["recommendation"],
                        True,
                    )
                else:
                    logger.warning("Groq output invalid, trying OpenRouter...")
            except Exception as e:
                logger.warning(f"Groq failed: {e}, trying OpenRouter...")

        # 2. Try OpenRouter (fallback)
        if self.openrouter:
            try:
                result = await self.openrouter.predict_financial_runway(
                    balance, transactions, features
                )
                if result and self._validate_llm_output(result):
                    logger.info("✅ Prediction via OpenRouter (fallback)")
                    return (
                        result["days_left"],
                        result["confidence"],
                        result["risk_level"],
                        result["recommendation"],
                        True,
                    )
                else:
                    logger.warning("OpenRouter output invalid, using statistical...")
            except Exception as e:
                logger.warning(f"OpenRouter failed: {e}, using statistical...")

        # 3. Statistical model (last resort)
        logger.info("📊 Using statistical prediction (all LLMs unavailable)")
        days_left, confidence, risk, rec = self._statistical_predict(balance, features)
        return days_left, confidence, risk, rec, False

    def _validate_llm_output(self, output: Dict) -> bool:
        """
        CRITICAL: Validate LLM output to prevent injection attacks.
        Ensures output conforms to expected schema.
        """
        required_fields = ["days_left", "risk_level", "confidence", "recommendation"]

        # Check all required fields present
        for field in required_fields:
            if field not in output:
                logger.error(f"LLM output missing field: {field}")
                return False

        # Validate days_left
        try:
            days_left = float(output["days_left"])
            if days_left < 0 or days_left > 10000:  # Reasonable bounds
                logger.error(f"Invalid days_left: {days_left}")
                return False
        except (ValueError, TypeError):
            logger.error(f"Invalid days_left type: {output['days_left']}")
            return False

        # Validate risk_level (must be one of allowed values)
        if output["risk_level"] not in ["safe", "warning", "danger", "critical"]:
            logger.error(f"Invalid risk_level: {output['risk_level']}")
            return False

        # Validate confidence (must be 0-1)
        try:
            confidence = float(output["confidence"])
            if confidence < 0 or confidence > 1:
                logger.error(f"Invalid confidence: {confidence}")
                return False
        except (ValueError, TypeError):
            logger.error(f"Invalid confidence type: {output['confidence']}")
            return False

        # Validate recommendation (reasonable length, no injection patterns)
        recommendation = str(output["recommendation"])
        if len(recommendation) > 500:
            logger.error(f"Recommendation too long: {len(recommendation)}")
            return False

        # Check for injection patterns in recommendation
        dangerous_patterns = [
            r"<script",
            r"javascript:",
            r"onerror=",
            r"onclick=",
            r"eval\(",
            r"exec\(",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, recommendation, re.IGNORECASE):
                logger.error(f"Dangerous pattern in recommendation: {pattern}")
                return False

        return True

    def _statistical_predict(
        self, balance: float, features: Dict
    ) -> Tuple[float, float, str, str]:
        """Fallback statistical prediction"""
        adjusted_spend = 0.6 * features["rolling_7d"] + 0.4 * features["rolling_30d"]

        if features["trend_slope"] > 0:
            adjusted_spend *= 1 + min(features["trend_slope"] * 0.5, 0.3)

        adjusted_spend += features["volatility"] * 0.5
        adjusted_spend = max(adjusted_spend, 1.0)

        days_left = balance / adjusted_spend
        confidence = self._calc_confidence(features)

        if days_left <= 3:
            risk = "critical"
        elif days_left <= 7:
            risk = "danger"
        elif days_left <= 14:
            risk = "warning"
        else:
            risk = "safe"

        if risk == "critical":
            rec = f"🚨 Критично! Осталось {int(days_left)} дней"
        elif risk == "danger":
            rec = f"⚠️ Внимание! Осталось {int(days_left)} дней"
        elif risk == "warning":
            rec = f"📊 У тебя {int(days_left)} дней до нуля"
        else:
            rec = f"✅ Всё хорошо! Денег хватит на {int(days_left)} дней"

        return days_left, confidence, risk, rec

    def _calc_trend(self, arr: np.ndarray) -> float:
        """Calculate trend slope"""
        if len(arr) < 2:
            return 0.0
        x = np.arange(len(arr))
        slope = np.polyfit(x, arr, 1)[0]
        return slope / (np.mean(arr) + 1e-6)

    def _calc_confidence(self, features: Dict) -> float:
        """Calculate confidence score"""
        conf = 0.5
        txns = features["total_txns"]
        if txns >= 30:
            conf += 0.25
        elif txns >= 15:
            conf += 0.15
        elif txns >= 7:
            conf += 0.10
        if features["volatility"] < features["daily_avg"] * 0.3:
            conf += 0.10
        return max(0.3, min(0.95, conf))

    def _default_features(self) -> Dict:
        """Default features for insufficient data"""
        return {
            "daily_avg": 0.0,
            "rolling_7d": 0.0,
            "rolling_30d": 0.0,
            "volatility": 0.0,
            "trend_slope": 0.0,
            "total_txns": 0,
        }
