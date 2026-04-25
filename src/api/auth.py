# -*- coding: utf-8 -*-
"""API Key Authentication middleware."""

from fastapi import Header, HTTPException
from src.config import Config


async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key nếu được cấu hình."""
    if not Config.API_KEY:
        return True  # No API key configured = open access
    if x_api_key != Config.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True
