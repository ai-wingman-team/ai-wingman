"""
Database connection management.

Provides async connection pooling and session management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text

from ai_wingman.config import settings
from ai_wingman.utils import logger


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self) -> None:
        """Initialize database manager."""
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def create_engine(self) -> AsyncEngine:
        """Create async database engine with connection pooling."""

        logger.info(
            f"Creating database engine: {settings.postgres_host}:{settings.postgres_port}"
        )

        # Choose pool based on environment
        if settings.app_env == "development":
            # NullPool for development (no connection pooling)
            pool_class = NullPool
            logger.debug("Using NullPool (no connection pooling)")
        else:
            # QueuePool for production
            pool_class = QueuePool
            logger.debug("Using QueuePool (connection pooling enabled)")

        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # Log all SQL statements in debug mode
            poolclass=pool_class,
            pool_size=5,  # Number of connections to maintain
            max_overflow=10,  # Max connections beyond pool_size
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        return engine

    @property
    def engine(self) -> AsyncEngine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = self.create_engine()
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Don't expire objects after commit
            )
        return self._session_factory

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session (context manager).

        Usage:
            async with db_manager.get_session() as session:
                result = await session.execute(query)
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """
        Check database connectivity.

        Returns:
            True if database is accessible, False otherwise.
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            logger.info("Database health check: OK")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


# Convenience function for getting sessions
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session (convenience function).

    Usage:
        async with get_session() as session:
            result = await session.execute(query)
    """
    async with db_manager.get_session() as session:
        yield session


__all__ = ["DatabaseManager", "db_manager", "get_session"]
