"""Shared data structures for context ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ContextSource(str, Enum):
    """Supported context data sources."""

    SLACK = "slack"
    MANUAL = "manual"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ContextMessage:
    """Normalized representation of an ingested context message."""

    source: ContextSource
    message_id: str
    timestamp: datetime
    content: str
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    thread_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> Dict[str, Any]:
        """Return a JSON-serializable payload for logging or debugging."""

        return {
            "source": self.source.value,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "thread_id": self.thread_id,
            "metadata": self.metadata,
        }

    def ensure_timezone(self) -> "ContextMessage":
        """Ensure timestamp is timezone-aware (UTC)."""

        ts = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        return ContextMessage(
            source=self.source,
            message_id=self.message_id,
            timestamp=ts,
            content=self.content,
            user_id=self.user_id,
            channel_id=self.channel_id,
            thread_id=self.thread_id,
            metadata=self.metadata,
        )


@dataclass(frozen=True, slots=True)
class StorageResult:
    """Outcome of storing a context message."""

    created: bool
    version: int
    is_latest: bool
    record_id: str
