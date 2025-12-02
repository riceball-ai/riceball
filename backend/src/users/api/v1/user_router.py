from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import fastapi_users, current_active_user
from src.auth.manager import get_user_manager, UserManager
from src.database import get_async_session
from src.users.models import User
from src.files.storage import storage_service
from .schemas import UserRead, UserUpdate, UserProfileUpdate

router = APIRouter(
    prefix='/users'
)


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    user: User = Depends(current_active_user),
):
    """
    Get current user with full avatar URL.
    Overwrites the default /me endpoint from fastapi-users to ensure avatar_url is a full URL.
    """
    # Convert to Pydantic model first to avoid modifying the DB object
    user_data = UserRead.model_validate(user)
    
    if user_data.avatar_url and not user_data.avatar_url.startswith(('http://', 'https://')):
        # Convert relative path to full URL
        from src.files.storage import storage_service
        user_data.avatar_url = await storage_service.get_public_url(user_data.avatar_url)
    
    return user_data


@router.put("/profile", response_model=UserRead)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    update_dict = {}
    if profile_update.nickname is not None:
        update_dict["name"] = profile_update.nickname
    if profile_update.avatar_url is not None:
        # If relative path (uploaded file), convert to full URL
        if profile_update.avatar_url and not profile_update.avatar_url.startswith(('http://', 'https://')):
             # Assuming frontend sends file path, we need to get full public URL
             # Note: Assuming avatar_url is a path stored on S3
             full_url = await storage_service.get_public_url(profile_update.avatar_url)
             update_dict["avatar_url"] = full_url
        else:
             update_dict["avatar_url"] = profile_update.avatar_url
    
    if not update_dict:
        return user

    user = await user_manager.update(user_update=UserUpdate(**update_dict), user=user)
    return user


router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate, requires_verification=True)
)

