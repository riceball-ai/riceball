"""
Authentication module

This module provides authentication-related dependencies and utilities.
"""

from .fastapi_users import (
    auth_backend,
    fastapi_users,
    current_active_user,
    current_active_user_optional,
    current_user,
    current_superuser
)
from .dependencies import get_user_db
from .manager import get_user_manager
from .oauth_service import get_oauth_service

__all__ = [
    "current_active_user",
    "current_active_user_optional",
    "current_user", 
    "current_superuser",
    "auth_backend",
    "fastapi_users",
    "get_user_db",
    "get_user_manager",
    "get_oauth_service"
]