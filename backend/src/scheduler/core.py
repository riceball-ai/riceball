import logging
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import async_session_maker
from src.scheduler.models import ScheduledTask
from src.scheduler.executor import execute_scheduled_task 

logger = logging.getLogger(__name__)

# Global Scheduler Instance
scheduler = AsyncIOScheduler()

async def start_scheduler():
    """Start the scheduler and load existing tasks"""
    logger.info("Starting APScheduler...")
    scheduler.start()
    
    # Initial Load
    async with async_session_maker() as session:
        await sync_scheduler_jobs(session)

async def sync_scheduler_jobs(session: AsyncSession):
    """
    Sync DB tasks with Scheduler in-memory jobs.
    Simple strategy: Remove all and re-add active ones.
    """
    logger.info("Syncing scheduled tasks...")
    scheduler.remove_all_jobs()
    
    stmt = select(ScheduledTask).where(ScheduledTask.is_active == True)
    result = await session.execute(stmt)
    tasks = result.scalars().all()
    
    for task in tasks:
        add_job_to_scheduler(task)
        
    logger.info(f"Synced {len(tasks)} tasks.")

def add_job_to_scheduler(task: ScheduledTask):
    try:
        trigger = None
        # Handle "Run Once" special prefix
        if task.cron_expression.startswith("ONCE:"):
            try:
                dt_str = task.cron_expression.replace("ONCE:", "")
                # ISO Format: YYYY-MM-DDTHH:MM:SS
                run_date = datetime.fromisoformat(dt_str)
                
                # If run_date is in past, verify if it already ran?
                # For now, simplistic approach: Schedule it if it's active.
                # APScheduler handles past dates by running immediately if misfire_grace_time allows,
                # or skipping. Default is run immediately if missed locally recently.
                trigger = DateTrigger(run_date=run_date)
            except ValueError as e:
                logger.error(f"Invalid Date format for task {task.id}: {e}")
                return
        else:
            # Note: from_crontab requires 5 fields.
            try:
                trigger = CronTrigger.from_crontab(task.cron_expression, timezone=task.timezone)
            except ValueError:
                # Fallback or specific error logging
                 logger.error(f"Invalid Cron format for task {task.id}: {task.cron_expression}")
                 return
        
        if trigger:
            scheduler.add_job(
                execute_scheduled_task,
                trigger,
                id=str(task.id),
                replace_existing=True,
                args=[task.id],
                name=task.name
            )
            logger.info(f"Added job {task.id}: {task.name} ({task.cron_expression})")
    except Exception as e:
        logger.error(f"Failed to add job {task.id}: {e}")

def remove_job_from_scheduler(task_id: str):
    try:
        scheduler.remove_job(task_id)
        logger.info(f"Removed job {task_id}")
    except Exception:
        pass
