"""Slack integration adapter that converts Slack payloads into context records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from ai_wingman.config import settings
from ai_wingman.storage.context_models import ContextMessage, ContextSource
from ai_wingman.storage.service import ContextStorageService
from ai_wingman.utils import logger


DEFAULT_SKIP_SUBTYPES: Sequence[str] = (
    "message_deleted",
    "tombstone",
    "channel_join",
    "channel_leave",
    "channel_topic",
    "channel_purpose",
    "channel_name",
    "channel_archive",
    "channel_unarchive",
)


@dataclass(slots=True)
class SlackAdapterConfig:
    """Configuration options controlling Slack ingestion."""

    channel_filter: Optional[Sequence[str]] = None
    skip_subtypes: Sequence[str] = DEFAULT_SKIP_SUBTYPES


class SlackAdapter:
    """Adapter that fetches Slack data and stores it via the context service."""

    def __init__(
        self,
        storage_service: ContextStorageService | None = None,
        bot_token: Optional[str] = None,
        client: Optional[AsyncWebClient] = None,
        config: Optional[SlackAdapterConfig] = None,
    ) -> None:
        self._storage = storage_service or ContextStorageService()
        token = bot_token or settings.slack_bot_token
        if client is None and token is None:
            raise ValueError("Slack bot token is required to initialize the adapter")
        self._client = client or AsyncWebClient(token=token)
        self._config = config or SlackAdapterConfig()

    @staticmethod
    def build_context_message(
        message: Dict[str, Any],
        *,
        channel_id: str,
        skip_subtypes: Optional[Sequence[str]] = None,
    ) -> Optional[ContextMessage]:
        """Translate a Slack message payload into a ContextMessage."""

        if message.get("type") != "message":
            return None

        subtype = message.get("subtype")
        skip_lookup = set(skip_subtypes or DEFAULT_SKIP_SUBTYPES)
        if subtype and subtype in skip_lookup:
            return None

        text = message.get("text")
        if not text:
            return None

        message_id = message.get("client_msg_id") or message.get("ts")
        if not message_id:
            return None

        edited_info = message.get("edited")
        timestamp_str = None
        if isinstance(edited_info, dict) and edited_info.get("ts"):
            timestamp_str = edited_info.get("ts")
        else:
            timestamp_str = message.get("ts")

        if not timestamp_str:
            return None

        timestamp = datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)

        metadata: Dict[str, Any] = {
            "ts": message.get("ts"),
            "edited": edited_info,
            "permalink": message.get("permalink"),
            "blocks": message.get("blocks"),
            "attachments": message.get("attachments"),
            "subtype": subtype,
        }
        # Remove empty values to keep metadata concise
        metadata = {key: value for key, value in metadata.items() if value is not None}

        context_message = ContextMessage(
            source=ContextSource.SLACK,
            message_id=message_id,
            timestamp=timestamp,
            content=text,
            user_id=message.get("user"),
            channel_id=channel_id,
            thread_id=message.get("thread_ts"),
            metadata=metadata,
        )

        return context_message

    async def ingest_message(self, message: Dict[str, Any], *, channel_id: str) -> Optional[str]:
        """Store a single Slack message payload."""

        context_message = self.build_context_message(
            message,
            channel_id=channel_id,
            skip_subtypes=self._config.skip_subtypes,
        )
        if context_message is None:
            logger.debug(
                "Skipping Slack message that did not produce context: {}", message
            )
            return None

        result = await self._storage.store(context_message)
        logger.debug(
            "Ingested Slack message source={} message_id={} version={} created={}",
            context_message.source.value,
            context_message.message_id,
            result.version,
            result.created,
        )
        return result.record_id

    async def ingest_messages(self, messages: Iterable[Dict[str, Any]], *, channel_id: str) -> List[str]:
        """Store multiple Slack messages."""

        context_messages: List[ContextMessage] = []
        for message in messages:
            context_message = self.build_context_message(
                message,
                channel_id=channel_id,
                skip_subtypes=self._config.skip_subtypes,
            )
            if context_message is not None:
                context_messages.append(context_message)

        if not context_messages:
            return []

        results = await self._storage.store_many(context_messages)
        logger.debug(
            "Stored {} Slack messages for channel {}", len(results), channel_id
        )
        return [result.record_id for result in results]

    async def fetch_and_ingest_channel(
        self,
        channel_id: str,
        *,
        limit: int = 200,
        oldest: Optional[float] = None,
    ) -> List[str]:
        """Fetch channel history from Slack and ingest the messages."""

        if self._config.channel_filter and channel_id not in self._config.channel_filter:
            logger.debug("Channel {} not in filter; skipping fetch", channel_id)
            return []

        try:
            response = await self._client.conversations_history(
                channel=channel_id,
                limit=limit,
                oldest=oldest,
            )
        except SlackApiError as exc:
            error_detail = exc.response.get("error") if getattr(exc, "response", None) else str(exc)
            logger.error(
                "Failed to fetch Slack history channel={} error={}",
                channel_id,
                error_detail,
            )
            raise

        messages: Sequence[Dict[str, Any]] = response.get("messages", [])
        # Slack returns newest first; reverse for chronological ordering
        ordered = list(reversed(messages))
        return await self.ingest_messages(ordered, channel_id=channel_id)


__all__ = ["SlackAdapter", "SlackAdapterConfig"]
