"""Service orchestrating context message persistence."""

from __future__ import annotations

from collections.abc import Iterable
from typing import List

from ai_wingman.database.connection import DatabaseManager, db_manager
from ai_wingman.database import operations
from ai_wingman.storage.context_models import ContextMessage, StorageResult
from ai_wingman.utils import logger


class ContextStorageService:
    """Persist normalized context messages using the hybrid append strategy."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self._db = database or db_manager

    async def store(self, message: ContextMessage) -> StorageResult:
        """Store a single context message."""

        normalized = message.ensure_timezone()
        async with self._db.get_session() as session:
            record, created = await operations.append_context_message(
                session,
                source=normalized.source.value,
                message_id=normalized.message_id,
                content=normalized.content,
                message_timestamp=normalized.timestamp,
                user_id=normalized.user_id,
                metadata=normalized.metadata,
                channel_id=normalized.channel_id,
                thread_id=normalized.thread_id,
            )

            result = StorageResult(
                created=created,
                version=record.version,
                is_latest=record.is_latest,
                record_id=str(record.id),
            )

        logger.debug(
            "Stored context message source={} message_id={} version={} created={}",
            normalized.source.value,
            normalized.message_id,
            result.version,
            result.created,
        )
        return result

    async def store_many(self, messages: Iterable[ContextMessage]) -> List[StorageResult]:
        """Store multiple context messages in a single transaction."""

        normalized = [msg.ensure_timezone() for msg in messages]
        if not normalized:
            return []

        async with self._db.get_session() as session:
            results: List[StorageResult] = []
            for message in normalized:
                record, created = await operations.append_context_message(
                    session,
                    source=message.source.value,
                    message_id=message.message_id,
                    content=message.content,
                    message_timestamp=message.timestamp,
                    user_id=message.user_id,
                    metadata=message.metadata,
                    channel_id=message.channel_id,
                    thread_id=message.thread_id,
                )
                results.append(
                    StorageResult(
                        created=created,
                        version=record.version,
                        is_latest=record.is_latest,
                        record_id=str(record.id),
                    )
                )

        logger.debug("Stored {} context messages", len(results))
        return results