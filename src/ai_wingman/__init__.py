"""
AI Wingman - Personal AI assistant with context memory.

A RAG-based system that stores Slack conversations and provides
intelligent responses using local LLM inference.
"""

__version__ = "0.1.0"
__author__ = "Femi & Yongjun"

from ai_wingman.config import settings
from ai_wingman.database import get_session, db_manager
from ai_wingman.utils import logger

__all__ = [
    "__version__",
    "__author__",
    "settings",
    "get_session",
    "db_manager",
    "logger",
]
