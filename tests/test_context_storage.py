"""Tests for the generic context storage service and adapters."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ai_wingman.database import operations
from ai_wingman.storage.context_models import ContextMessage, ContextSource
from ai_wingman.storage.service import ContextStorageService
from ai_wingman.integrations.manual_adapter import ManualInputAdapter
from ai_wingman.integrations.slack_adapter import SlackAdapter


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_store_context_message_creates_record(clean_db):
    """Storing a new context message should persist a record."""

    service = ContextStorageService()
    message = ContextMessage(
        source=ContextSource.MANUAL,
        message_id="manual-1",
        timestamp=datetime.now(timezone.utc),
        content="Manual context message",
        user_id="user-123",
        metadata={"source": "test"},
    )

    result = await service.store(message)

    assert result.created is True
    assert result.version == 1
    assert result.is_latest is True
    assert result.record_id


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_store_context_message_detects_duplicate(clean_db):
    """Identical message payloads should not create duplicate rows."""

    service = ContextStorageService()
    timestamp = datetime.now(timezone.utc)
    message = ContextMessage(
        source=ContextSource.MANUAL,
        message_id="manual-2",
        timestamp=timestamp,
        content="Duplicate context",
        metadata={"flag": True},
    )

    first = await service.store(message)
    second = await service.store(message)

    assert first.created is True
    assert second.created is False
    assert second.version == first.version


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_store_context_message_handles_edit(clean_db):
    """A later timestamp should create a new version while retaining history."""

    service = ContextStorageService()
    base_timestamp = datetime.now(timezone.utc)
    message_id = "manual-3"

    initial = ContextMessage(
        source=ContextSource.MANUAL,
        message_id=message_id,
        timestamp=base_timestamp,
        content="First draft",
    )

    edited = ContextMessage(
        source=ContextSource.MANUAL,
        message_id=message_id,
        timestamp=base_timestamp + timedelta(seconds=5),
        content="Revised draft",
    )

    await service.store(initial)
    await service.store(edited)

    latest = await operations.get_latest_context_message(
        clean_db,
        ContextSource.MANUAL.value,
        message_id,
    )
    assert latest is not None
    assert latest.version == 2
    assert latest.is_latest is True
    assert latest.content == "Revised draft"


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_store_context_message_same_timestamp_update(clean_db):
    """If the content changes with identical timestamp, keep the newest as latest."""

    service = ContextStorageService()
    timestamp = datetime.now(timezone.utc)
    message_id = "manual-4"

    original = ContextMessage(
        source=ContextSource.MANUAL,
        message_id=message_id,
        timestamp=timestamp,
        content="Original",
    )

    replacement = ContextMessage(
        source=ContextSource.MANUAL,
        message_id=message_id,
        timestamp=timestamp,
        content="Updated",
        metadata={"revision": 1},
    )

    await service.store(original)
    await service.store(replacement)

    latest = await operations.get_latest_context_message(
        clean_db,
        ContextSource.MANUAL.value,
        message_id,
    )

    assert latest is not None
    assert latest.content == "Updated"
    assert latest.version == 2
    assert latest.is_latest is True


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_manual_adapter_ingest(clean_db):
    """Manual adapter should normalize content before storage."""

    adapter = ManualInputAdapter()
    result = await adapter.ingest("Manual content", user_id="tester")

    assert result.created is True
    assert result.version == 1


@pytest.mark.asyncio
async def test_slack_adapter_builds_context_message():
    """Slack adapter should build context message with edited timestamp."""

    sample_payload = {
        "type": "message",
        "text": "Updated text",
        "user": "U123",
        "ts": "1700000000.000100",
        "client_msg_id": "abc-123",
        "channel": "C123",
        "thread_ts": "1700000000.000100",
        "edited": {"user": "U123", "ts": "1700000005.000100"},
    }

    context_message = SlackAdapter.build_context_message(
        sample_payload,
        channel_id="C123",
    )

    assert context_message is not None
    assert context_message.message_id == "abc-123"
    assert context_message.timestamp.timestamp() == pytest.approx(1700000005.0001)
    assert context_message.metadata["edited"]["ts"] == "1700000005.000100"