"""
Admin User Management API
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page, paginate
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_async_session
from src.users.models import User
from .schemas import UserRead, UserUpdate, UserAdminUpdate

router = APIRouter(prefix='/users')


@router.get('', response_model=Page[UserRead])
async def list_users(
    search: Optional[str] = Query(None, description="Search user email or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    is_superuser: Optional[bool] = Query(None, description="Filter by superuser status"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get user list (paginated)
    
    Supports search and filtering
    """
    # Build query
    query = select(User)
    
    # Search conditions
    if search:
        search_filter = or_(
            User.email.ilike(f'%{search}%'),
            User.name.ilike(f'%{search}%')
        )
        query = query.where(search_filter)
    
    # Status filtering
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if is_verified is not None:
        query = query.where(User.is_verified == is_verified)
    
    if is_superuser is not None:
        query = query.where(User.is_superuser == is_superuser)
    
    # Order by creation time descending
    query = query.order_by(User.created_at.desc())
    
    # Execute query
    result = await session.execute(query)
    users = result.scalars().all()
    
    # Get user balance info - REMOVED: Billing system no longer exists
    # Fill balance info - REMOVED: Billing system no longer exists
    for user in users:
        user.balance = 0
        user.total_recharged = 0
    
    # Use fastapi-pagination for pagination
    return paginate(users)


@router.get('/{user_id}', response_model=UserRead)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Get single user details"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.patch('/{user_id}', response_model=UserRead)
async def update_user(
    user_id: UUID,
    user_update: UserAdminUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update user info
    
    Admin can update all fields of a user
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await session.commit()
    await session.refresh(user)
    
    return user


@router.delete('/{user_id}')
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete user
    
    Note: This is a hard delete operation
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await session.delete(user)
    await session.commit()
    
    return {"message": "User deleted successfully"}


@router.get('/stats/summary')
async def get_user_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get user statistics
    """
    # Total users
    total_result = await session.execute(select(func.count(User.id)))
    total_users = total_result.scalar()
    
    # Active users
    active_result = await session.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )
    active_users = active_result.scalar()
    
    # Verified users
    verified_result = await session.execute(
        select(func.count(User.id)).where(User.is_verified.is_(True))
    )
    verified_users = verified_result.scalar()
    
    # Admin users
    admin_result = await session.execute(
        select(func.count(User.id)).where(User.is_superuser.is_(True))
    )
    admin_users = admin_result.scalar()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "admin_users": admin_users
    }
