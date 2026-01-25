import pytest
import asyncio
import pytest_asyncio
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.main import app
from src.models import Base

# Import all models to ensure they are registered with Base.metadata
import src.users.models
import src.ai_models.models
import src.assistants.models
import src.channels.models
import src.scheduler.models
# Add others as needed

from src.database import get_async_session


# TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_DATABASE_URL = "sqlite+aiosqlite:///./testing.db"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a session-level event loop"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True to view SQL statements
        future=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_database(test_engine):
    """Create database tables"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_session_maker(test_engine):
    """Create async session maker"""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def session(async_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for testing"""
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client and override database dependency"""
    
    async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        yield session
    
    # Override database dependency
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()
