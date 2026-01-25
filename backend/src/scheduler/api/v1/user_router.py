import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_async_session
from src.auth import current_active_user, current_superuser
from src.users.models import User
from src.scheduler.models import ScheduledTask
from src.scheduler.schemas import ScheduledTaskCreate, ScheduledTaskRead, ScheduledTaskUpdate
from src.scheduler.core import add_job_to_scheduler, remove_job_from_scheduler

router = APIRouter(prefix="/scheduled-tasks", tags=["Scheduled Tasks"])

@router.post("/", response_model=ScheduledTaskRead, status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    task_in: ScheduledTaskCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    # TODO: Verify binding belongs to user or is public
    task = ScheduledTask(
        **task_in.model_dump(),
        owner_id=user.id
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    
    if task.is_active:
        add_job_to_scheduler(task)
        
    return task

@router.get("/", response_model=List[ScheduledTaskRead])
async def list_scheduled_tasks(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    query = select(ScheduledTask).where(ScheduledTask.owner_id == user.id)
    result = await session.execute(query)
    return result.scalars().all()

@router.patch("/{task_id}", response_model=ScheduledTaskRead)
async def update_scheduled_task(
    task_id: uuid.UUID,
    task_in: ScheduledTaskUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    task = await session.get(ScheduledTask, task_id)
    if not task or task.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    await session.commit()
    await session.refresh(task)
    
    # Sync Scheduler
    if task.is_active:
        add_job_to_scheduler(task)
    else:
        remove_job_from_scheduler(str(task.id))
        
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(
    task_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    task = await session.get(ScheduledTask, task_id)
    if not task or task.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await session.delete(task)
    await session.commit()
    
    remove_job_from_scheduler(str(task.id))
