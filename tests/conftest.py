"""
Pytest configuration and fixtures.

Provides reusable test components for all tests.
"""

import asyncio
from typing import AsyncGenerator, Generator
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from ai_wingman.config import settings
from ai_wingman.database.models import Base
from ai_wingman.database.connection import db_manager


# ============================================================================
# Pytest Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for async tests.

    Scope: session (one loop for all tests)
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine.

    Uses the database configured in .env (should be test database).
    """
    engine = create_async_engine(
        settings.database_url,
        echo=False,  # Don't log SQL during tests
        pool_pre_ping=True,
    )

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test.

    Automatically rolls back after each test to keep tests isolated.
    """
    # Create a connection
    async with test_engine.connect() as connection:
        # Begin a transaction
        transaction = await connection.begin()

        # Create session bound to this connection
        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with session_factory() as session:
            yield session

            # Rollback transaction after test
            await transaction.rollback()


@pytest.fixture(scope="function")
async def clean_db(db_session: AsyncSession) -> AsyncSession:
    """
    Provide a clean database session with all tables created.

    This fixture ensures tables exist and are empty for each test.
    """
    # Create all tables (if they don't exist)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Clean all tables
    await db_session.execute(text("DELETE FROM ai_wingman.slack_messages"))
    await db_session.execute(text("DELETE FROM ai_wingman.user_contexts"))
    await db_session.execute(text("DELETE FROM ai_wingman.conversation_threads"))
    await db_session.commit()

    return db_session


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_message_data() -> dict:
    """Sample Slack message data for testing."""
    return {
        "slack_message_id": "1234567890.123456",
        "channel_id": "C01234567",
        "channel_name": "general",
        "user_id": "U01234567",
        "user_name": "testuser",
        "message_text": "This is a test message for AI Wingman",
        "message_type": "message",
        "slack_timestamp": 1234567890.123456,
        "metadata": {"source": "test", "tags": ["test", "sample"]},
    }


@pytest.fixture
def sample_embedding() -> list[float]:
    """Sample 384-dimensional embedding vector."""
    return [0.1] * 384  # Simple vector for testing


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user context data."""
    return {
        "user_id": "U01234567",
        "user_name": "testuser",
    }


@pytest.fixture
def sample_thread_data() -> dict:
    """Sample conversation thread data."""
    return {
        "thread_ts": 1234567890.123456,
        "channel_id": "C01234567",
    }


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
async def db_health_check() -> bool:
    """Check if database is accessible."""
    try:
        is_healthy = await db_manager.health_check()
        if not is_healthy:
            pytest.skip("Database is not accessible")
        return is_healthy
    except Exception as e:
        pytest.skip(f"Database health check failed: {e}")
