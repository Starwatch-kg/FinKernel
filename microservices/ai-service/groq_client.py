"""
GROQ CLIENT - Primary LLM provider with rate limit tracking
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

logger = setup_logger("groq_client")
config = get_config()


class RateLimitTracker:
    """Track API rate limits from response headers"""

    def __init__(self, provider: str):
        self.provider = provider
        self.remaining_requests: Optional[int] = None
        self.remaining_tokens: Optional[int] = None
        self.limit_requests: Optional[int] = None
        self.limit_tokens: Optional[int] = None
        self.reset_requests: Optional[str] = None
        self.reset_tokens: Optional[str] = None

    def update(self, headers: dict):
        """Parse rate limit info from response headers"""
        self.remaining_requests = _safe_int(headers.get("x-ratelimit-remaining-requests"))
        self.remaining_tokens = _safe_int(headers.get("x-ratelimit-remaining-tokens"))
        self.limit_requests = _safe_int(headers.get("x-ratelimit-limit-requests"))
        self.limit_tokens = _safe_int(headers.get("x-ratelimit-limit-tokens"))
        self.reset_requests = headers.get("x-ratelimit-reset-requests")
        self.reset_tokens = headers.get("x-ratelimit-reset-tokens")

        logger.info(
            f"[{self.provider}] Rate limits — "
            f"requests: {self.remaining_requests}/{self.limit_requests}, "
            f"tokens: {self.remaining_tokens}/{self.limit_tokens}"
        )

    @property
    def is_near_limit(self) -> bool:
        """Check if we're close to hitting rate limits"""
        if self.remaining_requests is not None and self.remaining_requests <= 2:
            return True
        if self.remaining_tokens is not None and self.remaining_tokens <= 500:
            return True
        return False

    @property
    def is_exhausted(self) -> bool:
        """Check if rate limits are exhausted"""
        if self.remaining_requests is not None and self.remaining_requests <= 0:
            return True
        if self.remaining_tokens is not None and self.remaining_tokens <= 0:
            return True
        return False


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


class GroqClient:
    """Groq LLM client with rate limit tracking"""

    def __init__(self):
        self.api_key = config.groq_api_key
        self.base_url = config.groq_base_url
        self.model = config.groq_model
        self.rate_tracker = RateLimitTracker("Groq")

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"Groq client initialized with model: {self.model}")
        else:
            self.client = None
            logger.warning("Groq API key not configured")

    async def predict_financial_runway(
        self, balance: float, transactions: list, features: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use Groq LLM to predict financial runway.
        Returns None on failure (caller should fallback).
        """
        if not self.client:
            return None

        # Skip if rate limits exhausted
        if self.rate_tracker.is_exhausted:
            logger.warning("Groq rate limits exhausted, skipping")
            return None

        prompt = self._build_prompt(balance, transactions, features)

        max_retries = 2
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
                    timeout=8.0,
                )

                # Parse rate limits from raw response if available
                if hasattr(response, '_raw_response') and hasattr(response._raw_response, 'headers'):
                    self.rate_tracker.update(dict(response._raw_response.headers))

                content = response.choices[0].message.content
                result = self._parse_output(content)

                if result:
                    result["ai_used"] = True
                    result["ai_provider"] = "groq"
                    logger.info(f"Groq prediction successful for balance ${balance:.2f}")
                    return result
                else:
                    logger.warning(f"Groq output parsing failed on attempt {attempt + 1}")

            except Exception as e:
                error_str = str(e)
                # Check for rate limit errors
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    logger.warning(f"Groq rate limited: {e}")
                    self.rate_tracker.remaining_requests = 0
                    return None  # Immediately fallback
                logger.warning(f"Groq attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(1)

        return None

    def _build_prompt(
        self, balance: float, transactions: list, features: Dict
    ) -> str:
        """Build prompt with sanitized transaction data"""
        recent_txns = transactions[:10] if len(transactions) > 10 else transactions

        txn_lines = []
        for t in recent_txns:
            txn_lines.append(
                f"- ${t['amount']:.2f} ({t['type']}) on {t['timestamp'][:10]}"
            )

        txn_summary = "\n".join(txn_lines)

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

    def _parse_output(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse and validate LLM JSON output"""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            required = ["days_left", "risk_level", "confidence", "explanation", "recommendation"]
            for field in required:
                if field not in data:
                    return None

            try:
                days_left = float(data["days_left"])
                if days_left < 0 or days_left > 10000:
                    return None
                data["days_left"] = days_left
            except (ValueError, TypeError):
                return None

            try:
                confidence = float(data["confidence"])
                data["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                return None

            if data["risk_level"] not in ["safe", "warning", "danger", "critical"]:
                data["risk_level"] = "warning"

            data["explanation"] = sanitize_for_llm(str(data["explanation"]), max_length=150)
            data["recommendation"] = sanitize_for_llm(str(data["recommendation"]), max_length=150)

            return data

        except json.JSONDecodeError:
            return None
        except Exception:
            return None
