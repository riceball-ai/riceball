import uuid
from typing import Optional
from datetime import datetime
from pydantic import EmailStr, BaseModel
from fastapi_users import schemas
from decimal import Decimal

class UserRead(schemas.BaseUser[uuid.UUID]):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    balance: Optional[Decimal] = None
    total_recharged: Optional[Decimal] = None


class UserUpdate(schemas.CreateUpdateDictModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserAdminUpdate(UserUpdate):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None