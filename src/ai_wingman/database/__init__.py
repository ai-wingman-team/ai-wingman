"""Database module."""

from ai_wingman.database.connection import (
    DatabaseManager,
    db_manager,
    get_session,
)
from ai_wingman.database.models import (
    Base,
    SlackMessage,
    UserContext,
    ConversationThread,
)
from ai_wingman.database import operations

__all__ = [
    # Connection
    "DatabaseManager",
    "db_manager",
    "get_session",
    # Models
    "Base",
    "SlackMessage",
    "UserContext",
    "ConversationThread",
    # Operations module
    "operations",
]
