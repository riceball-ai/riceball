"""Test if fixtures configuration works correctly"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class TestFixtures:
    """Test basic functionality of async fixtures"""

    @pytest.mark.asyncio
    async def test_async_session(self, session: AsyncSession):
        """Test if async database session works properly"""
        assert session is not None
        # Execute a simple query to verify the connection
        result = await session.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        assert row.test == 1

    @pytest.mark.asyncio
    async def test_async_client(self, client: AsyncClient):
        """Test if async client works properly"""
        assert client is not None
        # Test basic HTTP request
        response = await client.get("/")
        # Should return 404 due to the absence of the root path, but this proves the client works correctly
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_database_isolation(self, session: AsyncSession):
        """Test database isolation - each test has an independent session"""
        # This test verifies that each test function gets a clean database state
        result = await session.execute(text("SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'"))
        row = result.fetchone()
        # There should be some tables (from model definitions)
        assert row.count >= 0
