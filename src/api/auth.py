# -*- coding: utf-8 -*-
"""
API Key Authentication
=======================
Optional API key authentication for VietIDP endpoints.

Set VIETIDP_API_KEY environment variable to enable.
"""

import os
from src.config import Config


def verify_api_key(api_key: str = None) -> bool:
    """
    Verify API key nếu được cấu hình.

    Args:
        api_key: Key từ request header

    Returns:
        True nếu hợp lệ hoặc không cần auth
    """
    configured_key = Config.API_KEY
    if not configured_key:
        return True  # No auth required
    return api_key == configured_key
