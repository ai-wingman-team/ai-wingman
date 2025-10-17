"""
Test database models and operations.
"""

import pytest
from uuid import UUID
from ai_wingman.database import operations
from ai_wingman.database.models import SlackMessage, UserContext, ConversationThread


# ============================================================================
# Slack Message Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_create_slack_message(clean_db, sample_message_data):
    """Test creating a Slack message."""
    message = await operations.create_slack_message(clean_db, **sample_message_data)

    assert message is not None
    assert isinstance(message.id, UUID)
    assert message.slack_message_id == sample_message_data["slack_message_id"]
    assert message.message_text == sample_message_data["message_text"]
    assert message.is_deleted is False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_create_message_with_embedding(
    clean_db, sample_message_data, sample_embedding
):
    """Test creating a message with embedding."""
    message = await operations.create_slack_message(
        clean_db, **sample_message_data, embedding=sample_embedding
    )

    assert message.embedding is not None
    assert len(message.embedding) == 384


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_get_message_by_id(clean_db, sample_message_data):
    """Test retrieving message by internal ID."""
    # Create message
    created = await operations.create_slack_message(clean_db, **sample_message_data)
    await clean_db.commit()

    # Retrieve by ID
    retrieved = await operations.get_slack_message_by_id(clean_db, created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.message_text == sample_message_data["message_text"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_get_message_by_slack_id(clean_db, sample_message_data):
    """Test retrieving message by Slack ID."""
    # Create message
    await operations.create_slack_message(clean_db, **sample_message_data)
    await clean_db.commit()

    # Retrieve by Slack ID
    retrieved = await operations.get_slack_message_by_slack_id(
        clean_db, sample_message_data["slack_message_id"]
    )

    assert retrieved is not None
    assert retrieved.slack_message_id == sample_message_data["slack_message_id"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_get_messages_by_user(clean_db, sample_message_data):
    """Test retrieving messages by user."""
    # Create multiple messages
    for i in range(3):
        data = sample_message_data.copy()
        data["slack_message_id"] = f"msg_{i}"
        data["slack_timestamp"] = 1234567890.0 + i
        await operations.create_slack_message(clean_db, **data)
    await clean_db.commit()

    # Retrieve by user
    messages = await operations.get_messages_by_user(
        clean_db, sample_message_data["user_id"]
    )

    assert len(messages) == 3
    assert all(msg.user_id == sample_message_data["user_id"] for msg in messages)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_soft_delete_message(clean_db, sample_message_data):
    """Test soft deleting a message."""
    # Create message
    message = await operations.create_slack_message(clean_db, **sample_message_data)
    await clean_db.commit()

    # Soft delete
    deleted = await operations.soft_delete_message(clean_db, message.id)
    await clean_db.commit()

    assert deleted is True

    # Verify it's marked as deleted
    retrieved = await operations.get_slack_message_by_id(clean_db, message.id)
    assert retrieved.is_deleted is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_message_count(clean_db, sample_message_data):
    """Test counting messages."""
    # Create messages
    for i in range(5):
        data = sample_message_data.copy()
        data["slack_message_id"] = f"msg_{i}"
        await operations.create_slack_message(clean_db, **data)
    await clean_db.commit()

    # Count all messages
    count = await operations.get_message_count(clean_db)
    assert count == 5

    # Count by user
    user_count = await operations.get_message_count(
        clean_db, user_id=sample_message_data["user_id"]
    )
    assert user_count == 5


# ============================================================================
# User Context Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_create_user_context(clean_db, sample_user_data):
    """Test creating user context."""
    context = await operations.create_user_context(clean_db, **sample_user_data)

    assert context is not None
    assert isinstance(context.id, UUID)
    assert context.user_id == sample_user_data["user_id"]
    assert context.total_messages == 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_get_or_create_user_context(clean_db, sample_user_data):
    """Test get_or_create pattern."""
    # First call creates
    context1 = await operations.get_or_create_user_context(clean_db, **sample_user_data)
    await clean_db.commit()

    # Second call retrieves existing
    context2 = await operations.get_or_create_user_context(
        clean_db, sample_user_data["user_id"]
    )

    assert context1.id == context2.id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_update_user_context_stats(clean_db, sample_user_data):
    """Test updating user statistics."""
    # Create context
    context = await operations.create_user_context(clean_db, **sample_user_data)
    assert context is not None 
    await clean_db.commit()

    # Update stats
    updated = await operations.update_user_context_stats(
        clean_db, sample_user_data["user_id"], increment_messages=5
    )
    await clean_db.commit()

    assert updated.total_messages == 5
    assert updated.first_message_at is not None
    assert updated.last_message_at is not None


# ============================================================================
# Conversation Thread Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_create_conversation_thread(clean_db, sample_thread_data):
    """Test creating conversation thread."""
    thread = await operations.create_conversation_thread(clean_db, **sample_thread_data)

    assert thread is not None
    assert isinstance(thread.id, UUID)
    assert thread.thread_ts == sample_thread_data["thread_ts"]
    assert thread.message_count == 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_update_thread_activity(clean_db, sample_thread_data):
    """Test updating thread activity."""
    # Create thread
    thread = await operations.create_conversation_thread(clean_db, **sample_thread_data)
    assert thread is not None 
    await clean_db.commit()

    # Update activity
    updated = await operations.update_thread_activity(
        clean_db, sample_thread_data["thread_ts"], increment_messages=3
    )
    await clean_db.commit()

    assert updated.message_count == 3
    assert updated.last_activity_at is not None


# ============================================================================
# Model Methods Tests
# ============================================================================


def test_slack_message_to_dict(sample_message_data):
    """Test SlackMessage.to_dict() method."""
    message = SlackMessage(**sample_message_data)
    message_dict = message.to_dict()

    assert isinstance(message_dict, dict)
    assert "slack_message_id" in message_dict
    assert "message_text" in message_dict
    assert "has_embedding" in message_dict


def test_user_context_to_dict(sample_user_data):
    """Test UserContext.to_dict() method."""
    context = UserContext(**sample_user_data)
    context_dict = context.to_dict()

    assert isinstance(context_dict, dict)
    assert "user_id" in context_dict
    assert "total_messages" in context_dict


def test_conversation_thread_to_dict(sample_thread_data):
    """Test ConversationThread.to_dict() method."""
    thread = ConversationThread(**sample_thread_data)
    thread_dict = thread.to_dict()

    assert isinstance(thread_dict, dict)
    assert "thread_ts" in thread_dict
    assert "message_count" in thread_dict
