from collections.abc import AsyncGenerator
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from .config import settings

# Handle SQLite specific configuration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    
    # Ensure database directory exists for SQLite
    # Remove protocol prefix
    db_path = settings.DATABASE_URL.split(":///")[-1]
    if db_path and db_path != ":memory:":
        try:
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create database directory: {e}")

engine = create_async_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session