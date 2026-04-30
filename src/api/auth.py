# -*- coding: utf-8 -*-
"""API Key Authentication middleware."""

import logging

from fastapi import Header, HTTPException, status

from src.config import Config

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: str | None = Header(default=None)):
    """Verify API key with explicit fail-closed behavior when required."""
    if Config.REQUIRE_API_KEY and not Config.API_KEY:
        logger.error("API authentication is required but VIETIDP_API_KEY is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is required but the server is not configured correctly.",
        )

    if not Config.API_KEY:
        return True

    if x_api_key != Config.API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")

    return True
