"""Adapter handling manually submitted context messages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from ai_wingman.storage.context_models import ContextMessage, ContextSource, StorageResult
from ai_wingman.storage.service import ContextStorageService


class ManualInputAdapter:
    """Convert manual inputs into context messages and persist them."""

    def __init__(self, storage_service: ContextStorageService | None = None) -> None:
        self._storage = storage_service or ContextStorageService()

    async def ingest(
        self,
        content: str,
        *,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        channel_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> StorageResult:
        if not content.strip():
            raise ValueError("Manual input content cannot be empty")

        message = ContextMessage(
            source=ContextSource.MANUAL,
            message_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            content=content,
            user_id=user_id,
            channel_id=channel_id,
            thread_id=thread_id,
            metadata=metadata or {},
        )

        return await self._storage.store(message)


__all__ = ["ManualInputAdapter"]
