import uuid

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy
)

from src.config import settings
from src.users.models import User

from .manager import get_user_manager

cookie_transport = CookieTransport(
    cookie_name="access-token",
    cookie_httponly=True,
    cookie_secure=True,
    cookie_samesite="lax",
)

def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    return JWTStrategy(
        secret=settings.SECRET_KEY, 
        lifetime_seconds=settings.ACCESS_TOKEN_LIFETIME_SECONDS
    )

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    auth_backends=[auth_backend]
)

# User dependencies
current_active_user = fastapi_users.current_user(active=True)
current_active_user_optional = fastapi_users.current_user(active=True, optional=True)
current_user = fastapi_users.current_user()
current_superuser = fastapi_users.current_user(active=True, superuser=True)