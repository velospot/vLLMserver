"""API key authentication for production safety."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class APIKeyValidator:
    """Simple API key validation (production: use database/Redis)."""

    # In production, load these from a secure store (database, HashiCorp Vault, etc.)
    ALLOWED_KEYS = {
        "sk-dev-test": "development",
        "sk-prod-primary": "production",
    }

    @staticmethod
    def validate(api_key: Optional[str]) -> str:
        """Validate API key and return tier.

        Args:
            api_key: Key from X-API-Key header

        Returns:
            Tier string (development, production)

        Raises:
            HTTPException: If key is missing or invalid
        """
        if not api_key:
            logger.warning("Request missing X-API-Key header")
            raise HTTPException(
                status_code=401, detail="Missing X-API-Key header"
            )

        tier = APIKeyValidator.ALLOWED_KEYS.get(api_key)
        if not tier:
            logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")

        return tier

    @staticmethod
    async def verify_from_request(request: Request) -> tuple[str, str]:
        """Extract and validate API key from request.

        Returns:
            Tuple of (api_key, tier)
        """
        api_key = request.headers.get("X-API-Key")
        tier = APIKeyValidator.validate(api_key)
        return api_key, tier
