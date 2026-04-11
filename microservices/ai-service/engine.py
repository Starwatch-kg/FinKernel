"""AI Prediction Engine with OpenRouter Integration"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from openrouter_client import OpenRouterClient
import sys
sys.path.append('/app')

from shared.logger import setup_logger

logger = setup_logger("prediction_engine")


class PredictionEngine:
    def __init__(self):
        self.min_txns = 3
        self.openrouter = OpenRouterClient()

    def calculate_features(self, transactions: List[Dict]) -> Dict:
        if not transactions:
            return self._default_features()

        expenses = [t['amount'] for t in transactions if t['type'] == 'expense']
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
            "total_txns": len(expenses)
        }

    async def predict(self, balance: float, features: Dict, transactions: List[Dict]) -> Tuple[Optional[float], float, str, str, bool]:
        """Predict using OpenRouter LLM with fallback to statistical model"""
        if features['total_txns'] < self.min_txns:
            return None, 0.3, "safe", "📊 Недостаточно данных", False

        if balance <= 0:
            return 0, 0.95, "critical", "⚠️ Баланс на нуле!", False

        # Try OpenRouter first
        try:
            llm_result = await self.openrouter.predict_financial_runway(
                balance, transactions, features
            )

            if llm_result:
                return (
                    llm_result["days_left"],
                    llm_result["confidence"],
                    llm_result["risk_level"],
                    llm_result["recommendation"],
                    True  # AI was used
                )
        except Exception as e:
            logger.warning(f"LLM prediction failed, using fallback: {e}")

        # Fallback to statistical model
        days_left, confidence, risk, rec = self._statistical_predict(balance, features)
        return days_left, confidence, risk, rec, False  # AI was NOT used

    def _statistical_predict(self, balance: float, features: Dict) -> Tuple[float, float, str, str]:
        """Fallback statistical prediction"""
        adjusted_spend = 0.6 * features['rolling_7d'] + 0.4 * features['rolling_30d']

        if features['trend_slope'] > 0:
            adjusted_spend *= (1 + min(features['trend_slope'] * 0.5, 0.3))

        adjusted_spend += features['volatility'] * 0.5
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
        if len(arr) < 2:
            return 0.0
        x = np.arange(len(arr))
        slope = np.polyfit(x, arr, 1)[0]
        return slope / (np.mean(arr) + 1e-6)

    def _calc_confidence(self, features: Dict) -> float:
        conf = 0.5
        txns = features['total_txns']
        if txns >= 30:
            conf += 0.25
        elif txns >= 15:
            conf += 0.15
        elif txns >= 7:
            conf += 0.10
        if features['volatility'] < features['daily_avg'] * 0.3:
            conf += 0.10
        return max(0.3, min(0.95, conf))

    def _default_features(self) -> Dict:
        return {
            "daily_avg": 0.0,
            "rolling_7d": 0.0,
            "rolling_30d": 0.0,
            "volatility": 0.0,
            "trend_slope": 0.0,
            "total_txns": 0
        }
