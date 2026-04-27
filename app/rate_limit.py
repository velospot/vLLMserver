"""Token-aware rate limiting (request-based in this version, Redis in production)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class TokenRateLimiter:
    """In-memory token-aware rate limiter.

    Production should use Redis for distributed rate limiting across multiple workers.
    This tracks three dimensions:
    - Requests per minute (RPM)
    - Tokens per minute (TPM)
    - Tokens per day (TPD)
    """

    def __init__(
        self,
        rpm_limit: int = 60,
        tpm_limit: int = 10000,
        tpd_limit: int = 1000000,
    ) -> None:
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.tpd_limit = tpd_limit

        # Per-user tracking: {user_id: {metric: [timestamp, value]}}
        self.usage: dict[str, dict[str, list[tuple[float, int]]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def check_and_record(
        self,
        user_id: str,
        estimated_prompt_tokens: int,
        estimated_completion_tokens: int,
    ) -> tuple[bool, Optional[str]]:
        """Check if request is allowed and record usage.

        Args:
            user_id: Identifier (API key, user ID, etc.)
            estimated_prompt_tokens: Input tokens
            estimated_completion_tokens: Expected output tokens

        Returns:
            Tuple of (allowed, error_message)
        """
        now = time.time()
        total_tokens = estimated_prompt_tokens + estimated_completion_tokens

        # Clean old entries (>1 min and >1 day)
        one_min_ago = now - 60
        one_day_ago = now - 86400

        for metric in ["rpm", "tpm_minute", "tpm_day"]:
            self.usage[user_id][metric] = [
                (ts, val)
                for ts, val in self.usage[user_id][metric]
                if ts > (one_day_ago if "day" in metric else one_min_ago)
            ]

        # Check RPM
        rpm_entries = self.usage[user_id]["rpm"]
        if len(rpm_entries) >= self.rpm_limit:
            return False, f"Rate limit exceeded: {self.rpm_limit} requests per minute"

        # Check TPM (minute)
        tpm_minute_entries = self.usage[user_id]["tpm_minute"]
        tpm_minute = sum(val for _, val in tpm_minute_entries)
        if tpm_minute + total_tokens > self.tpm_limit:
            remaining = self.tpm_limit - tpm_minute
            return False, f"Token limit exceeded: {remaining} tokens remaining this minute"

        # Check TPD (day)
        tpm_day_entries = self.usage[user_id]["tpm_day"]
        tpm_day = sum(val for _, val in tpm_day_entries)
        if tpm_day + total_tokens > self.tpd_limit:
            remaining = self.tpd_limit - tpm_day
            return False, f"Daily limit exceeded: {remaining} tokens remaining today"

        # Record usage
        self.usage[user_id]["rpm"].append((now, 1))
        self.usage[user_id]["tpm_minute"].append((now, total_tokens))
        self.usage[user_id]["tpm_day"].append((now, total_tokens))

        logger.debug(
            f"User {user_id}: {total_tokens} tokens (RPM: {len(rpm_entries)}, TPM: {tpm_minute}, TPD: {tpm_day})"
        )

        return True, None

    def get_usage_stats(self, user_id: str) -> dict[str, int]:
        """Get current usage statistics for a user."""
        now = time.time()
        one_min_ago = now - 60
        one_day_ago = now - 86400

        rpm_entries = [
            val for ts, val in self.usage[user_id]["rpm"] if ts > one_min_ago
        ]
        tpm_minute_entries = [
            val for ts, val in self.usage[user_id]["tpm_minute"] if ts > one_min_ago
        ]
        tpm_day_entries = [
            val for ts, val in self.usage[user_id]["tpm_day"] if ts > one_day_ago
        ]

        return {
            "requests_this_minute": len(rpm_entries),
            "tokens_this_minute": sum(tpm_minute_entries),
            "tokens_today": sum(tpm_day_entries),
            "rpm_limit": self.rpm_limit,
            "tpm_limit": self.tpm_limit,
            "tpd_limit": self.tpd_limit,
        }


# Global rate limiter instance
limiter = TokenRateLimiter(rpm_limit=60, tpm_limit=100000, tpd_limit=10000000)
