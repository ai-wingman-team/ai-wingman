"""
SQLAlchemy ORM models for AI Wingman.

Maps to PostgreSQL tables created in init.sql.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from ai_wingman.config import settings


# Base class for all models
class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class SlackMessage(Base):
    """
    Slack message with vector embedding.

    Maps to ai_wingman.slack_messages table.
    """

    __tablename__ = "slack_messages"
    __table_args__ = {"schema": "ai_wingman"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # Slack metadata
    slack_message_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    channel_name: Mapped[Optional[str]] = mapped_column(String(255))
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Message content
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), default="message")

    # Vector embedding (384 dimensions for all-MiniLM-L6-v2)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(settings.embedding_dimension)
    )

    # Timestamps
    slack_timestamp: Mapped[float] = mapped_column(
        Numeric(16, 6),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    # Additional metadata (flexible JSONB field)
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",  # Column name in DB
        JSONB,
        server_default="{}",
    )

    # Soft delete flag
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SlackMessage(id={self.id}, "
            f"user={self.user_name}, "
            f"channel={self.channel_name}, "
            f"text='{self.message_text[:50]}...')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding embedding for brevity)."""
        return {
            "id": str(self.id),
            "slack_message_id": self.slack_message_id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "message_text": self.message_text,
            "message_type": self.message_type,
            "slack_timestamp": float(self.slack_timestamp),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata_,
            "is_deleted": self.is_deleted,
            "has_embedding": self.embedding is not None,
        }


class UserContext(Base):
    """
    User context and preferences.

    Maps to ai_wingman.user_contexts table.
    """

    __tablename__ = "user_contexts"
    __table_args__ = {"schema": "ai_wingman"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # User identification
    user_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Aggregated insights
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    first_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # User patterns
    communication_style: Mapped[Optional[str]] = mapped_column(Text)
    topics_of_interest: Mapped[list[str]] = mapped_column(
        JSONB,
        server_default="[]",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<UserContext(id={self.id}, "
            f"user={self.user_name}, "
            f"messages={self.total_messages})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "user_name": self.user_name,
            "total_messages": self.total_messages,
            "first_message_at": (
                self.first_message_at.isoformat() if self.first_message_at else None
            ),
            "last_message_at": (
                self.last_message_at.isoformat() if self.last_message_at else None
            ),
            "communication_style": self.communication_style,
            "topics_of_interest": self.topics_of_interest,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationThread(Base):
    """
    Slack conversation thread metadata.

    Maps to ai_wingman.conversation_threads table.
    """

    __tablename__ = "conversation_threads"
    __table_args__ = {"schema": "ai_wingman"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # Thread identification
    thread_ts: Mapped[float] = mapped_column(
        Numeric(16, 6),
        unique=True,
        nullable=False,
    )
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Thread summary
    summary: Mapped[Optional[str]] = mapped_column(Text)
    participant_count: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ConversationThread(id={self.id}, "
            f"channel={self.channel_id}, "
            f"messages={self.message_count})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "thread_ts": float(self.thread_ts),
            "channel_id": self.channel_id,
            "summary": self.summary,
            "participant_count": self.participant_count,
            "message_count": self.message_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_activity_at": (
                self.last_activity_at.isoformat() if self.last_activity_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Export all models
__all__ = [
    "Base",
    "SlackMessage",
    "UserContext",
    "ConversationThread",
]
