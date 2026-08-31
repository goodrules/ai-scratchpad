"""Import smoke tests for every ADK agent under agents/adk/agents.

These catch breakage from google-adk upgrades: renamed/moved symbols, removed
APIs, and missing optional extras (mcp, a2a). Importing an agent module is
enough to exercise its full wiring, because ADK agents build their tool and
sub-agent graph at module scope.

No network or credentials required.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

AGENTS_DIR = Path(__file__).resolve().parents[2] / "agents" / "adk" / "agents"

# (agent id, directory to put on sys.path, module to import, expected root_agent type)
CASES = [
    ("doc_understanding", AGENTS_DIR, "doc_understanding.agent", "LlmAgent"),
    ("short_story_agent", AGENTS_DIR, "short_story_agent.agent", "Workflow"),
    ("google_search_agent", AGENTS_DIR / "google_search_agent", "app.agent", "LlmAgent"),
    ("ai_location_strategy", AGENTS_DIR / "ai-location-strategy", "app.agent", "LlmAgent"),
    (
        "travel_concierge",
        AGENTS_DIR / "travel-concierge",
        "travel_concierge.agent",
        "LlmAgent",
    ),
    (
        "software_bug_assistant",
        AGENTS_DIR / "software-bug-assistant",
        "software_bug_assistant.agent",
        "LlmAgent",
    ),
]


@pytest.mark.parametrize(
    ("agent_id", "path_entry", "module", "expected_type"),
    CASES,
    ids=[c[0] for c in CASES],
)
def test_agent_imports(
    agent_id: str, path_entry: Path, module: str, expected_type: str
) -> None:
    """Each agent's root_agent builds cleanly against the installed ADK."""
    sys.path.insert(0, str(path_entry))
    try:
        mod = importlib.import_module(module)
        root_agent = getattr(mod, "root_agent", None)
        assert root_agent is not None, f"{agent_id} exposes no root_agent"
        assert type(root_agent).__name__ == expected_type
    finally:
        sys.path.remove(str(path_entry))
