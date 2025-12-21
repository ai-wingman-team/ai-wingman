"""Integration adapters for external systems."""

from ai_wingman.integrations.manual_adapter import ManualInputAdapter
from ai_wingman.integrations.slack_adapter import SlackAdapter, SlackAdapterConfig

__all__ = [
    "ManualInputAdapter",
    "SlackAdapter",
    "SlackAdapterConfig",
]
