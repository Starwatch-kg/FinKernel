"""OpenRouter API Client"""
import os
import json
import asyncio
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
import sys
sys.path.append('/app')

from shared.config import get_config
from shared.logger import setup_logger

logger = setup_logger("openrouter")
config = get_config()


class OpenRouterClient:
    def __init__(self):
        self.api_key = config.openrouter_api_key
        self.base_url = config.openrouter_base_url
        self.model = config.openrouter_model

        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"OpenRouter client initialized with model: {self.model}")
        else:
            self.client = None
            logger.warning("OpenRouter API key not configured - using fallback statistical model")

    async def predict_financial_runway(
        self,
        balance: float,
        transactions: list,
        features: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to predict financial runway with structured output and retry logic"""
        if not self.client:
            return None

        prompt = self._build_prediction_prompt(balance, transactions, features)

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a financial AI assistant. Analyze user spending patterns and predict how many days their money will last. Return ONLY valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=500,
                    timeout=10.0  # 10 second timeout
                )

                content = response.choices[0].message.content
                result = self._parse_llm_output(content)
                result["ai_used"] = True  # Mark as AI-generated
                logger.info(f"LLM prediction successful for user balance ${balance:.2f}")
                return result

            except Exception as e:
                logger.warning(f"OpenRouter attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"OpenRouter API error after {max_retries} attempts: {e}")
                    return None
                # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(2 ** attempt)

    async def generate_ai_tips(
        self,
        balance: float,
        transactions: list,
        prediction: Dict[str, Any]
    ) -> list:
        """Generate personalized financial tips"""
        if not self.client:
            return []

        prompt = f"""Based on this financial data:
- Current balance: ${balance:.2f}
- Recent transactions: {len(transactions)} transactions
- Predicted days left: {prediction.get('days_left', 'unknown')}
- Risk level: {prediction.get('risk_level', 'unknown')}

Generate 3 short, actionable financial tips (max 100 chars each).
Return as JSON array: ["tip1", "tip2", "tip3"]"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial advisor. Be concise and actionable."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )

            content = response.choices[0].message.content
            tips = json.loads(content)
            return tips if isinstance(tips, list) else []

        except Exception as e:
            logger.error(f"Tips generation error: {e}")
            return []

    async def generate_lesson_content(
        self,
        topic: str,
        difficulty: str = "medium",
        user_context: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate adaptive lesson content"""
        if not self.client:
            return None

        prompt = f"""Create a financial education lesson about: {topic}
Difficulty: {difficulty}
User context: {json.dumps(user_context or {})}

Return JSON with this structure:
{{
  "title": "Lesson title",
  "content": "Lesson content (200-300 words)",
  "key_points": ["point1", "point2", "point3"],
  "questions": [
    {{
      "question": "Question text",
      "options": ["A", "B", "C", "D"],
      "correct": 0,
      "explanation": "Why this is correct"
    }}
  ]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial education expert. Create engaging, practical lessons."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            logger.error(f"Lesson generation error: {e}")
            return None

    async def generate_adaptive_question(
        self,
        topic: str,
        difficulty: str,
        user_mastery: float
    ) -> Optional[Dict[str, Any]]:
        """Generate adaptive question based on user mastery"""
        if not self.client:
            return None

        prompt = f"""Generate a {difficulty} difficulty question about: {topic}
User mastery level: {user_mastery:.2f}

Return JSON:
{{
  "question": "Question text",
  "options": ["A", "B", "C", "D"],
  "correct": 0,
  "explanation": "Explanation",
  "difficulty_score": 0.5
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial education expert creating adaptive questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=400
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            logger.error(f"Question generation error: {e}")
            return None

    def _build_prediction_prompt(self, balance: float, transactions: list, features: Dict) -> str:
        """Build structured prompt for prediction"""
        recent_txns = transactions[:10] if len(transactions) > 10 else transactions
        txn_summary = "\n".join([
            f"- ${t['amount']:.2f} ({t['type']}) on {t['timestamp']}"
            for t in recent_txns
        ])

        return f"""Analyze this financial situation:

Current Balance: ${balance:.2f}

Recent Transactions:
{txn_summary}

Spending Statistics:
- Daily average: ${features.get('daily_avg', 0):.2f}
- 7-day average: ${features.get('rolling_7d', 0):.2f}
- 30-day average: ${features.get('rolling_30d', 0):.2f}
- Volatility: ${features.get('volatility', 0):.2f}
- Trend: {features.get('trend_slope', 0):.4f}

Predict how many days the money will last. Return ONLY this JSON:
{{
  "days_left": <number>,
  "risk_level": "safe|warning|danger|critical",
  "confidence": <0.0-1.0>,
  "explanation": "Brief explanation (max 150 chars)",
  "recommendation": "Actionable advice (max 150 chars)"
}}"""

    def _parse_llm_output(self, content: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON output"""
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            # Validate required fields
            required = ["days_left", "risk_level", "confidence", "explanation", "recommendation"]
            for field in required:
                if field not in data:
                    raise ValueError(f"Missing field: {field}")

            # Validate types and ranges
            data["days_left"] = float(data["days_left"])
            data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))

            if data["risk_level"] not in ["safe", "warning", "danger", "critical"]:
                data["risk_level"] = "warning"

            return data

        except Exception as e:
            logger.error(f"Parse error: {e}")
            raise ValueError(f"Invalid LLM output: {content[:100]}")
