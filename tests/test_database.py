"""
Test database connection and health checks.
"""

import pytest
from ai_wingman.database import get_session


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_database_health_check(db_health_check):
    """Test database health check."""
    assert db_health_check is True


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_get_session(db_health_check):
    """Test that we can get a database session."""
    from ai_wingman.database import db_manager
    async with db_manager.get_session() as session:
        assert session is not None


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_session_commit(db_session):
    """Test session commit works."""
    await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_session_rollback(db_session):
    """Test session rollback works."""
    await db_session.rollback()


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_database_schema_exists(db_session):
    """Test that ai_wingman schema exists."""
    from sqlalchemy import text
    
    result = await db_session.execute(
        text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'ai_wingman'")
    )
    schema = result.scalar_one_or_none()
    assert schema == "ai_wingman"


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_pgvector_extension_exists(db_session):
    """Test that pgvector extension is installed."""
    from sqlalchemy import text
    
    result = await db_session.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    )
    ext = result.scalar_one_or_none()
    assert ext == "vector"
