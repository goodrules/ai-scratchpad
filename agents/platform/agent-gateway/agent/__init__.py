"""Custom Governed ADK Agent package for Google Cloud Agent Gateway demo.

Exposes the root agent, application entrypoint, factory constructor,
hybrid toolset resolver, and governed banking instruction prompts.
"""

from agent.agent import (
    app,
    create_agent,
    get_banking_tools,
    root_agent,
)
from agent.prompts import (
    ACTION_MENU_ITEMS,
    ACTION_MENU_TEXT,
    BANKING_INSTRUCTION,
    CONFIRMATION_THRESHOLD_USD,
    GOVERNANCE_POLICIES,
    VALID_CUSTOMER_IDS,
)

__all__ = [
    "root_agent",
    "app",
    "create_agent",
    "get_banking_tools",
    "BANKING_INSTRUCTION",
    "VALID_CUSTOMER_IDS",
    "ACTION_MENU_ITEMS",
    "ACTION_MENU_TEXT",
    "CONFIRMATION_THRESHOLD_USD",
    "GOVERNANCE_POLICIES",
]
