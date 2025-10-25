"""
Database CRUD operations.

Helper functions for common database tasks.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from ai_wingman.database.models import SlackMessage, UserContext, ConversationThread
from ai_wingman.utils import logger


# ============================================================================
# Slack Message Operations
# ============================================================================


async def create_slack_message(
    session: AsyncSession,
    slack_message_id: str,
    channel_id: str,
    user_id: str,
    message_text: str,
    slack_timestamp: float,
    channel_name: Optional[str] = None,
    user_name: Optional[str] = None,
    message_type: str = "message",
    embedding: Optional[List[float]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> SlackMessage:
    """
    Create a new Slack message record.

    Args:
        session: Database session
        slack_message_id: Unique Slack message ID
        channel_id: Slack channel ID
        user_id: Slack user ID
        message_text: Message content
        slack_timestamp: Slack timestamp
        channel_name: Optional channel name
        user_name: Optional user name
        message_type: Message type (default: "message")
        embedding: Optional vector embedding
        metadata: Optional metadata dictionary

    Returns:
        Created SlackMessage instance
    """
    message = SlackMessage(
        slack_message_id=slack_message_id,
        channel_id=channel_id,
        channel_name=channel_name,
        user_id=user_id,
        user_name=user_name,
        message_text=message_text,
        message_type=message_type,
        embedding=embedding,
        slack_timestamp=slack_timestamp,
        metadata_=metadata or {},
    )

    session.add(message)
    await session.flush()  # Flush to get the generated ID

    logger.info(f"Created Slack message: {message.slack_message_id}")
    return message


async def get_slack_message_by_id(
    session: AsyncSession,
    message_id: UUID,
) -> Optional[SlackMessage]:
    """
    Get Slack message by internal ID.

    Args:
        session: Database session
        message_id: Internal message UUID

    Returns:
        SlackMessage if found, None otherwise
    """
    stmt = select(SlackMessage).where(SlackMessage.id == message_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_slack_message_by_slack_id(
    session: AsyncSession,
    slack_message_id: str,
) -> Optional[SlackMessage]:
    """
    Get Slack message by Slack message ID.

    Args:
        session: Database session
        slack_message_id: Slack's message ID

    Returns:
        SlackMessage if found, None otherwise
    """
    stmt = select(SlackMessage).where(SlackMessage.slack_message_id == slack_message_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_messages_by_user(
    session: AsyncSession,
    user_id: str,
    limit: int = 100,
    include_deleted: bool = False,
) -> List[SlackMessage]:
    """
    Get messages by user ID.

    Args:
        session: Database session
        user_id: Slack user ID
        limit: Maximum number of messages
        include_deleted: Include soft-deleted messages

    Returns:
        List of SlackMessage instances
    """
    stmt = select(SlackMessage).where(SlackMessage.user_id == user_id)

    if not include_deleted:
        stmt = stmt.where(SlackMessage.is_deleted.is_(False))

    stmt = stmt.order_by(SlackMessage.slack_timestamp.desc()).limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_messages_by_channel(
    session: AsyncSession,
    channel_id: str,
    limit: int = 100,
    include_deleted: bool = False,
) -> List[SlackMessage]:
    """
    Get messages by channel ID.

    Args:
        session: Database session
        channel_id: Slack channel ID
        limit: Maximum number of messages
        include_deleted: Include soft-deleted messages

    Returns:
        List of SlackMessage instances
    """
    stmt = select(SlackMessage).where(SlackMessage.channel_id == channel_id)

    if not include_deleted:
        stmt = stmt.where(SlackMessage.is_deleted.is_(False))

    stmt = stmt.order_by(SlackMessage.slack_timestamp.desc()).limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def search_similar_messages(
    session: AsyncSession,
    query_embedding: List[float],
    similarity_threshold: float = 0.7,
    limit: int = 5,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
) -> List[tuple[SlackMessage, float]]:
    """Search for similar messages using vector similarity.

    Args:
        session: Database session
        query_embedding: Query vector embedding
        similarity_threshold: Minimum similarity score (0.0-1.0)
        limit: Maximum number of results
        user_id: Optional filter by user
        channel_id: Optional filter by channel

    Returns:
        List of (SlackMessage, similarity_score) tuples
    """
    # Use the SQL function we created in init.sql
    # Note: We'll use raw SQL here since pgvector operations are best done in SQL

    # Validate embedding values before string construction (security)
    if not query_embedding:
        raise ValueError("query_embedding cannot be empty")
    
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in query_embedding):
        raise ValueError("Embedding must contain only numeric values")
    
    # Convert embedding list to PostgreSQL vector format
    embedding_str = f"[{','.join(map(str, query_embedding))}]"

    # Build WHERE clause based on optional parameters
    where_clauses = [
        "sm.is_deleted = FALSE",
        "sm.embedding IS NOT NULL",
        f"1 - (sm.embedding <=> '{embedding_str}'::vector) >= :threshold",
    ]

    if user_id is not None:
        where_clauses.append("sm.user_id = :user_id")

    if channel_id is not None:
        where_clauses.append("sm.channel_id = :channel_id")

    where_clause = " AND ".join(where_clauses)

    # Use the dynamic WHERE clause
    query = text(
        f"""
        SELECT
            sm.*,
            1 - (sm.embedding <=> '{embedding_str}'::vector) AS similarity
        FROM ai_wingman.slack_messages sm
        WHERE {where_clause}
        ORDER BY sm.embedding <=> '{embedding_str}'::vector
        LIMIT :limit
    """
    )

    # Build parameters dict (no embedding needed now)
    params = {
        "threshold": similarity_threshold,
        "limit": limit,
    }

    if user_id is not None:
        params["user_id"] = user_id

    if channel_id is not None:
        params["channel_id"] = channel_id

    result = await session.execute(query, params)
    rows = result.fetchall()

    # Convert rows to SlackMessage objects
    messages_with_scores = []
    for row in rows:
        message = SlackMessage(
            id=row.id,
            slack_message_id=row.slack_message_id,
            channel_id=row.channel_id,
            channel_name=row.channel_name,
            user_id=row.user_id,
            user_name=row.user_name,
            message_text=row.message_text,
            message_type=row.message_type,
            embedding=row.embedding,
            slack_timestamp=row.slack_timestamp,
            created_at=row.created_at,
            updated_at=row.updated_at,
            metadata_=row.metadata,
            is_deleted=row.is_deleted,
        )
        similarity = float(row.similarity)
        messages_with_scores.append((message, similarity))

    logger.info(f"Found {len(messages_with_scores)} similar messages")
    return messages_with_scores


async def update_message_embedding(
    session: AsyncSession,
    message_id: UUID,
    embedding: List[float],
) -> Optional[SlackMessage]:
    """
    Update message embedding.

    Args:
        session: Database session
        message_id: Message UUID
        embedding: Vector embedding

    Returns:
        Updated SlackMessage if found
    """
    stmt = (
        update(SlackMessage)
        .where(SlackMessage.id == message_id)
        .values(embedding=embedding)
        .returning(SlackMessage)
    )

    result = await session.execute(stmt)
    message = result.scalar_one_or_none()

    if message:
        logger.info(f"Updated embedding for message: {message_id}")

    return message


async def soft_delete_message(
    session: AsyncSession,
    message_id: UUID,
) -> bool:
    """
    Soft delete a message.

    Args:
        session: Database session
        message_id: Message UUID

    Returns:
        True if deleted, False if not found
    """
    stmt = (
        update(SlackMessage)
        .where(SlackMessage.id == message_id)
        .values(is_deleted=True)
        .returning(SlackMessage.id)
    )

    result = await session.execute(stmt)
    deleted = result.scalar_one_or_none()

    if deleted:
        logger.info(f"Soft deleted message: {message_id}")
        return True
    return False


async def get_message_count(
    session: AsyncSession,
    user_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    include_deleted: bool = False,
) -> int:
    """
    Get count of messages.

    Args:
        session: Database session
        user_id: Optional filter by user
        channel_id: Optional filter by channel
        include_deleted: Include soft-deleted messages

    Returns:
        Message count
    """
    stmt = select(func.count(SlackMessage.id))

    if user_id:
        stmt = stmt.where(SlackMessage.user_id == user_id)
    if channel_id:
        stmt = stmt.where(SlackMessage.channel_id == channel_id)
    if not include_deleted:
        stmt = stmt.where(SlackMessage.is_deleted.is_(False))

    result = await session.execute(stmt)
    return result.scalar_one()


# ============================================================================
# User Context Operations
# ============================================================================


async def create_user_context(
    session: AsyncSession,
    user_id: str,
    user_name: Optional[str] = None,
) -> UserContext:
    """
    Create a new user context.

    Args:
        session: Database session
        user_id: Slack user ID
        user_name: Optional user name

    Returns:
        Created UserContext instance
    """
    context = UserContext(
        user_id=user_id,
        user_name=user_name,
    )

    session.add(context)
    await session.flush()

    logger.info(f"Created user context: {user_id}")
    return context


async def get_user_context(
    session: AsyncSession,
    user_id: str,
) -> Optional[UserContext]:
    """
    Get user context by user ID.

    Args:
        session: Database session
        user_id: Slack user ID

    Returns:
        UserContext if found
    """
    stmt = select(UserContext).where(UserContext.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_user_context(
    session: AsyncSession,
    user_id: str,
    user_name: Optional[str] = None,
) -> UserContext:
    """
    Get existing user context or create new one.

    Args:
        session: Database session
        user_id: Slack user ID
        user_name: Optional user name

    Returns:
        UserContext instance
    """
    context = await get_user_context(session, user_id)

    if context is None:
        context = await create_user_context(session, user_id, user_name)

    return context


async def update_user_context_stats(
    session: AsyncSession,
    user_id: str,
    increment_messages: int = 1,
) -> Optional[UserContext]:
    """
    Update user context statistics.

    Args:
        session: Database session
        user_id: Slack user ID
        increment_messages: Number to increment total_messages by

    Returns:
        Updated UserContext if found
    """
    # Get current context
    context = await get_user_context(session, user_id)
    if not context:
        return None

    # Update stats
    context.total_messages += increment_messages
    context.last_message_at = datetime.now(timezone.utc)

    if context.first_message_at is None:
        context.first_message_at = datetime.now(timezone.utc)

    await session.flush()

    logger.info(f"Updated stats for user: {user_id}")
    return context


# ============================================================================
# Conversation Thread Operations
# ============================================================================


async def create_conversation_thread(
    session: AsyncSession,
    thread_ts: float,
    channel_id: str,
) -> ConversationThread:
    """
    Create a new conversation thread.

    Args:
        session: Database session
        thread_ts: Slack thread timestamp
        channel_id: Slack channel ID

    Returns:
        Created ConversationThread instance
    """
    thread = ConversationThread(
        thread_ts=thread_ts,
        channel_id=channel_id,
        started_at=datetime.now(timezone.utc),
    )

    session.add(thread)
    await session.flush()

    logger.info(f"Created conversation thread: {thread_ts}")
    return thread


async def get_conversation_thread(
    session: AsyncSession,
    thread_ts: float,
) -> Optional[ConversationThread]:
    """
    Get conversation thread by thread timestamp.

    Args:
        session: Database session
        thread_ts: Slack thread timestamp

    Returns:
        ConversationThread if found
    """
    stmt = select(ConversationThread).where(ConversationThread.thread_ts == thread_ts)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_thread_activity(
    session: AsyncSession,
    thread_ts: float,
    increment_messages: int = 1,
) -> Optional[ConversationThread]:
    """
    Update thread activity.

    Args:
        session: Database session
        thread_ts: Slack thread timestamp
        increment_messages: Number to increment message_count by

    Returns:
        Updated ConversationThread if found
    """
    thread = await get_conversation_thread(session, thread_ts)
    if not thread:
        return None

    thread.message_count += increment_messages
    thread.last_activity_at = datetime.now(timezone.utc)

    await session.flush()

    logger.info(f"Updated thread activity: {thread_ts}")
    return thread


# ============================================================================
# Bulk Operations
# ============================================================================


async def bulk_create_messages(
    session: AsyncSession,
    messages: List[Dict[str, Any]],
) -> int:
    """
    Bulk insert Slack messages.

    Args:
        session: Database session
        messages: List of message dictionaries

    Returns:
        Number of messages created
    """
    message_objects = [SlackMessage(**msg_data) for msg_data in messages]
    session.add_all(message_objects)
    await session.flush()

    logger.info(f"Bulk created {len(message_objects)} messages")
    return len(message_objects)


# Export all operations
__all__ = [
    # Slack messages
    "create_slack_message",
    "get_slack_message_by_id",
    "get_slack_message_by_slack_id",
    "get_messages_by_user",
    "get_messages_by_channel",
    "search_similar_messages",
    "update_message_embedding",
    "soft_delete_message",
    "get_message_count",
    "bulk_create_messages",
    # User contexts
    "create_user_context",
    "get_user_context",
    "get_or_create_user_context",
    "update_user_context_stats",
    # Conversation threads
    "create_conversation_thread",
    "get_conversation_thread",
    "update_thread_activity",
]
