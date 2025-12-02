import uuid
from typing import Optional
from pydantic import EmailStr

from fastapi_users import schemas

class UserRead(schemas.BaseUser[uuid.UUID]):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    language: Optional[str] = None


class UserCreate(schemas.CreateUpdateDictModel):
    email: Optional[EmailStr] = None
    password: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    language: Optional[str] = 'en'  # Default language is English
    is_superuser: bool = False
    is_verified: bool = False
    is_active: bool = True


class UserRegisterRequest(UserCreate):
    pass


class ChangePasswordRequest(schemas.CreateUpdateDictModel):
    old_password: str
    new_password: str