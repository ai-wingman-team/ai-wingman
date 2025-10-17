#!/usr/bin/env python3
"""
AI Wingman Database Demo

Interactive demonstration of database operations.
Showcases creating messages, user contexts, and similarity search.
"""

import asyncio
import random
from datetime import datetime
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track

from ai_wingman.config import settings
from ai_wingman.database import get_session, operations
from ai_wingman.utils import logger


console = Console()


# ============================================================================
# Demo Data
# ============================================================================

SAMPLE_MESSAGES = [
    {
        "user_id": "U001",
        "user_name": "Alice",
        "channel_id": "C001",
        "channel_name": "general",
        "text": "Hey team! How's everyone doing today?",
    },
    {
        "user_id": "U002",
        "user_name": "Bob",
        "channel_id": "C001",
        "channel_name": "general",
        "text": "Working on the new feature for vector search. It's pretty cool!",
    },
    {
        "user_id": "U001",
        "user_name": "Alice",
        "channel_id": "C002",
        "channel_name": "random",
        "text": "Anyone want to grab coffee later?",
    },
    {
        "user_id": "U003",
        "user_name": "Charlie",
        "channel_id": "C001",
        "channel_name": "general",
        "text": "Just pushed the database migrations. Looking good!",
    },
    {
        "user_id": "U002",
        "user_name": "Bob",
        "channel_id": "C003",
        "channel_name": "tech-talk",
        "text": "PostgreSQL with pgvector is amazing for semantic search.",
    },
    {
        "user_id": "U003",
        "user_name": "Charlie",
        "channel_id": "C003",
        "channel_name": "tech-talk",
        "text": "Yeah, the HNSW index makes similarity search super fast!",
    },
    {
        "user_id": "U001",
        "user_name": "Alice",
        "channel_id": "C002",
        "channel_name": "random",
        "text": "Coffee at 3pm sounds perfect!",
    },
    {
        "user_id": "U004",
        "user_name": "Diana",
        "channel_id": "C001",
        "channel_name": "general",
        "text": "Great work everyone! The project is coming along nicely.",
    },
]


def generate_fake_embedding(seed: int) -> List[float]:
    """Generate a fake 384-dimensional embedding for demo purposes."""
    random.seed(seed)
    return [random.uniform(-1, 1) for _ in range(settings.embedding_dimension)]


# ============================================================================
# Demo Functions
# ============================================================================


async def demo_header():
    """Display demo header."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]AI Wingman Database Demo[/bold cyan]\n"
            "[dim]Showcasing PostgreSQL + pgvector operations[/dim]",
            border_style="cyan",
        )
    )
    console.print()


async def demo_health_check():
    """Demonstrate database health check."""
    console.print("[bold]1. Database Health Check[/bold]")

    from ai_wingman.database import db_manager

    is_healthy = await db_manager.health_check()

    if is_healthy:
        console.print(" Database connection: [green]OK[/green]")
    else:
        console.print(" Database connection: [red]FAILED[/red]")
        return False

    console.print()
    return True


async def demo_create_messages():
    """Demonstrate creating Slack messages."""
    console.print("[bold]2. Creating Sample Messages[/bold]")

    async with get_session() as session:
        created_count = 0

        for i, msg_data in enumerate(
            track(SAMPLE_MESSAGES, description="Creating messages...")
        ):
            # Generate unique Slack message ID
            slack_msg_id = f"msg_{datetime.now().timestamp()}_{i}"
            slack_ts = datetime.now().timestamp() + i

            # Create message with fake embedding
            message = await operations.create_slack_message(
                session,
                slack_message_id=slack_msg_id,
                channel_id=msg_data["channel_id"],
                channel_name=msg_data["channel_name"],
                user_id=msg_data["user_id"],
                user_name=msg_data["user_name"],
                message_text=msg_data["text"],
                slack_timestamp=slack_ts,
                embedding=generate_fake_embedding(i),
                metadata={"demo": True, "index": i},
            )
            created_count += 1

        await session.commit()
        console.print(f" Created {created_count} messages")

    console.print()


async def demo_query_messages():
    """Demonstrate querying messages."""
    console.print("[bold]3. Querying Messages[/bold]")

    async with get_session() as session:
        # Get messages by user
        alice_messages = await operations.get_messages_by_user(
            session,
            user_id="U001",
        )
        console.print(f" Alice has {len(alice_messages)} messages")

        # Get messages by channel
        general_messages = await operations.get_messages_by_channel(
            session,
            channel_id="C001",
        )
        console.print(f" #general has {len(general_messages)} messages")

        # Get total count
        total_count = await operations.get_message_count(session)
        console.print(f" Total messages: {total_count}")

    console.print()


async def demo_display_messages():
    """Display messages in a formatted table."""
    console.print("[bold]4. Recent Messages[/bold]")

    async with get_session() as session:
        # Get all messages
        all_messages = await operations.get_messages_by_channel(
            session,
            channel_id="C001",
            limit=100,
        )

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("User", style="green")
        table.add_column("Channel", style="yellow")
        table.add_column("Message", style="white")
        table.add_column("Has Embedding", style="magenta")

        for msg in all_messages[:5]:  # Show first 5
            table.add_row(
                msg.user_name or msg.user_id,
                msg.channel_name or msg.channel_id,
                msg.message_text[:50] + ("..." if len(msg.message_text) > 50 else ""),
                "" if msg.embedding else "",
            )

        console.print(table)

    console.print()


async def demo_user_contexts():
    """Demonstrate user context operations."""
    console.print("[bold]5. User Contexts[/bold]")

    async with get_session() as session:
        # Create user contexts
        users = {
            "U001": "Alice",
            "U002": "Bob",
            "U003": "Charlie",
            "U004": "Diana",
        }

        for user_id, user_name in users.items():
            # Get or create context
            context = await operations.get_or_create_user_context(
                session,
                user_id=user_id,
                user_name=user_name,
            )

            # Count user's messages
            msg_count = await operations.get_message_count(session, user_id=user_id)

            # Update context stats
            if msg_count > 0:
                await operations.update_user_context_stats(
                    session,
                    user_id=user_id,
                    increment_messages=msg_count,
                )

        await session.commit()

        # Display user contexts
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("User", style="green")
        table.add_column("Total Messages", style="yellow")
        table.add_column("First Message", style="white")
        table.add_column("Last Message", style="white")

        for user_id in users.keys():
            context = await operations.get_user_context(session, user_id)
            if context:
                table.add_row(
                    context.user_name or context.user_id,
                    str(context.total_messages),
                    (
                        context.first_message_at.strftime("%H:%M:%S")
                        if context.first_message_at
                        else "N/A"
                    ),
                    (
                        context.last_message_at.strftime("%H:%M:%S")
                        if context.last_message_at
                        else "N/A"
                    ),
                )

        console.print(table)

    console.print()


async def demo_similarity_search():
    """Demonstrate vector similarity search."""
    console.print("[bold]6. Similarity Search (Demo)[/bold]")
    console.print(
        "[dim]Note: Using fake embeddings for demo. Real embeddings would use sentence-transformers.[/dim]"
    )
    console.print()

    async with get_session() as session:
        # Use a fake query embedding (similar to one of our messages)
        query_embedding = generate_fake_embedding(1)  # Similar to Bob's first message

        # Search for similar messages
        similar = await operations.search_similar_messages(
            session,
            query_embedding=query_embedding,
            similarity_threshold=0.0,  # Low threshold since embeddings are random
            limit=3,
        )

        if similar:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("User", style="green")
            table.add_column("Message", style="white")
            table.add_column("Similarity", style="magenta")

            for message, score in similar:
                table.add_row(
                    message.user_name or message.user_id,
                    message.message_text[:60]
                    + ("..." if len(message.message_text) > 60 else ""),
                    f"{score:.4f}",
                )

            console.print(table)
        else:
            console.print(" No similar messages found")

    console.print()


async def demo_soft_delete():
    """Demonstrate soft delete functionality."""
    console.print("[bold]7. Soft Delete[/bold]")

    async with get_session() as session:
        # Get a message to delete
        messages = await operations.get_messages_by_user(session, "U001", limit=1)

        if messages:
            message = messages[0]
            console.print(f" Deleting message: '{message.message_text[:50]}...'")

            # Soft delete
            deleted = await operations.soft_delete_message(session, message.id)
            await session.commit()

            if deleted:
                console.print(" Message soft deleted")

                # Verify it's still in database but marked deleted
                retrieved = await operations.get_slack_message_by_id(
                    session, message.id
                )
                console.print(f" is_deleted flag: {retrieved.is_deleted}")

                # Count excluding deleted
                active_count = await operations.get_message_count(
                    session, include_deleted=False
                )
                total_count = await operations.get_message_count(
                    session, include_deleted=True
                )
                console.print(f" Active messages: {active_count}, Total: {total_count}")

    console.print()


async def demo_summary():
    """Display final summary."""
    console.print("[bold]8. Summary[/bold]")

    async with get_session() as session:
        total_messages = await operations.get_message_count(
            session, include_deleted=True
        )
        active_messages = await operations.get_message_count(
            session, include_deleted=False
        )

        # Count users
        from sqlalchemy import select, func
        from ai_wingman.database.models import UserContext

        user_count_stmt = select(func.count(UserContext.id))
        result = await session.execute(user_count_stmt)
        user_count = result.scalar_one()

        console.print(
            Panel.fit(
                f"[bold cyan]Demo Complete![/bold cyan]\n\n"
                f" Total Messages: {total_messages}\n"
                f" Active Messages: {active_messages}\n"
                f" Users: {user_count}\n"
                f"  Database: PostgreSQL + pgvector\n"
                f" Embedding Dimension: {settings.embedding_dimension}",
                border_style="green",
            )
        )


async def cleanup():
    """Cleanup demo data."""
    console.print()
    console.print("[dim]Cleaning up demo data...[/dim]")

    from sqlalchemy import text

    async with get_session() as session:
        # Delete all demo data
        await session.execute(
            text(
                "DELETE FROM ai_wingman.slack_messages WHERE metadata->>'demo' = 'true'"
            )
        )
        await session.execute(text("DELETE FROM ai_wingman.user_contexts"))
        await session.commit()

    console.print("[dim] Cleanup complete[/dim]")


# ============================================================================
# Main Demo
# ============================================================================


async def main():
    """Run the complete demo."""
    try:
        await demo_header()

        # Check database health
        if not await demo_health_check():
            console.print("[red]Database is not available. Exiting.[/red]")
            return

        # Run demos
        await demo_create_messages()
        await demo_query_messages()
        await demo_display_messages()
        await demo_user_contexts()
        await demo_similarity_search()
        await demo_soft_delete()
        await demo_summary()

        # Cleanup
        await cleanup()

        console.print()
        console.print("[bold green] Demo completed successfully![/bold green]")
        console.print()

    except Exception as e:
        console.print(f"[red]Error during demo: {e}[/red]")
        logger.exception("Demo failed")
        raise
    finally:
        # Close database connections
        from ai_wingman.database import db_manager

        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
