"""
SECURE OPENROUTER CLIENT - Prompt injection protection
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

sys.path.append("/app")

from shared.config import get_config
from shared.logger import setup_logger
from shared.security_hardening import sanitize_for_llm

logger = setup_logger("openrouter_secure")
config = get_config()


class OpenRouterClient:
    def __init__(self):
        self.api_key = config.openrouter_api_key
        self.base_url = config.openrouter_base_url
        self.model = config.openrouter_model

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"OpenRouter client initialized with model: {self.model}")
        else:
            self.client = None
            logger.warning(
                "OpenRouter API key not configured - using fallback statistical model"
            )

    async def predict_financial_runway(
        self, balance: float, transactions: list, features: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to predict financial runway with SANITIZED inputs.
        All user data is sanitized before building prompt.
        """
        if not self.client:
            return None

        # Build prompt with SANITIZED data
        prompt = self._build_safe_prediction_prompt(balance, transactions, features)

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a financial AI assistant. "
                                "Analyze user spending patterns and predict how many days their money will last. "
                                "Return ONLY valid JSON with the exact structure specified. "
                                "Do not include any other text or explanation."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                    timeout=10.0,
                )

                content = response.choices[0].message.content
                result = self._parse_llm_output(content)

                if result:
                    result["ai_used"] = True
                    logger.info(f"LLM prediction successful for balance ${balance:.2f}")
                    return result
                else:
                    logger.warning(
                        f"LLM output parsing failed on attempt {attempt + 1}"
                    )

            except Exception as e:
                logger.warning(
                    f"OpenRouter attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(
                        f"OpenRouter API error after {max_retries} attempts: {e}"
                    )
                    return None
                await asyncio.sleep(2**attempt)

        return None

    def _build_safe_prediction_prompt(
        self, balance: float, transactions: list, features: Dict
    ) -> str:
        """
        Build prompt with SANITIZED transaction data.
        CRITICAL: All user input is sanitized to prevent prompt injection.
        """
        # Take only recent transactions and sanitize
        recent_txns = transactions[:10] if len(transactions) > 10 else transactions

        # Build transaction summary with SANITIZED descriptions
        txn_lines = []
        for t in recent_txns:
            # Sanitize description (already sanitized in main_secure.py, but double-check)
            safe_desc = sanitize_for_llm(t.get("description", ""), max_length=50)

            # Build safe transaction line
            txn_lines.append(
                f"- ${t['amount']:.2f} ({t['type']}) on {t['timestamp'][:10]}"
                # Note: NOT including description to minimize injection risk
            )

        txn_summary = "\n".join(txn_lines)

        # Build prompt with only numerical and controlled data
        return f"""Analyze this financial situation:

Current Balance: ${balance:.2f}

Recent Transactions (last 10):
{txn_summary}

Spending Statistics:
- Daily average: ${features.get('daily_avg', 0):.2f}
- 7-day average: ${features.get('rolling_7d', 0):.2f}
- 30-day average: ${features.get('rolling_30d', 0):.2f}
- Volatility: ${features.get('volatility', 0):.2f}
- Trend: {features.get('trend_slope', 0):.4f}

Predict how many days the money will last. Return ONLY this JSON structure:
{{
  "days_left": <number between 0 and 1000>,
  "risk_level": "<one of: safe, warning, danger, critical>",
  "confidence": <number between 0.0 and 1.0>,
  "explanation": "<brief explanation, max 100 chars>",
  "recommendation": "<actionable advice, max 100 chars>"
}}

Do not include any other text. Return only the JSON."""

    def _parse_llm_output(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse and VALIDATE LLM JSON output.
        CRITICAL: Strict validation to prevent injection.
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON
            data = json.loads(content)

            # Validate required fields
            required = [
                "days_left",
                "risk_level",
                "confidence",
                "explanation",
                "recommendation",
            ]
            for field in required:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return None

            # Validate and sanitize types
            try:
                days_left = float(data["days_left"])
                if days_left < 0 or days_left > 10000:
                    logger.error(f"days_left out of range: {days_left}")
                    return None
                data["days_left"] = days_left
            except (ValueError, TypeError):
                logger.error(f"Invalid days_left: {data['days_left']}")
                return None

            # Validate confidence
            try:
                confidence = float(data["confidence"])
                data["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                logger.error(f"Invalid confidence: {data['confidence']}")
                return None

            # Validate risk_level
            if data["risk_level"] not in ["safe", "warning", "danger", "critical"]:
                logger.error(f"Invalid risk_level: {data['risk_level']}")
                data["risk_level"] = "warning"

            # Sanitize text fields
            data["explanation"] = sanitize_for_llm(
                str(data["explanation"]), max_length=150
            )
            data["recommendation"] = sanitize_for_llm(
                str(data["recommendation"]), max_length=150
            )

            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
