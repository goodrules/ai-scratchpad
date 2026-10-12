"""Enterprise Governed ADK Banking Agent for Google Cloud Agent Gateway demo.

Constructs an enterprise-grade banking agent powered by Google Cloud ADK,
featuring hybrid toolset resolution (Google Cloud Agent Registry vs. local FastMCP),
resilient model configuration (Gemini 3.8 Flash with retry policies),
and strict governance adherence (SGP-01 AML policies, Model Armor, IAM controls).
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional, Union

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.adk.tools import FunctionTool
from google.genai import types

from agent.prompts import BANKING_INSTRUCTION
from mcp_server.server import (
    get_account,
    get_transaction_history,
    lookup_customer_by_phone,
    pay_bill,
    transfer_to_phone,
)

logger = logging.getLogger("banking_agent")


def _has_gcp_credentials() -> bool:
    """Check if GCP application default credentials or explicit credentials are configured."""
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return True
    try:
        import google.auth

        _, project = google.auth.default()
        return bool(
            project
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCP_PROJECT")
        )
    except Exception:
        return False


def _should_use_registry(mode: str) -> bool:
    """Determine whether to use Agent Registry toolset based on mode and environment."""
    if mode == "registry":
        return True
    if mode == "local":
        return False
    if mode == "auto":
        server_name = os.environ.get("MCP_SERVER_NAME")
        if server_name and _has_gcp_credentials():
            return True
        return False
    raise ValueError(
        f"Unsupported toolset mode: '{mode}'. Must be 'auto', 'local', or 'registry'."
    )


def _get_local_banking_tools() -> List[FunctionTool]:
    """Load local banking tools wrapped as ADK FunctionTools."""
    return [
        FunctionTool(get_account),
        FunctionTool(lookup_customer_by_phone),
        FunctionTool(transfer_to_phone),
        FunctionTool(pay_bill),
        FunctionTool(get_transaction_history),
    ]


def _get_registry_banking_tools(mcp_server_name: Optional[str] = None) -> List[Any]:
    """Load banking tools via Google Cloud Agent Registry McpToolset."""
    from google.adk.integrations.agent_registry import AgentRegistry

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    raw_location = os.environ.get("AGENT_REGISTRY_LOCATION") or os.environ.get(
        "GOOGLE_CLOUD_LOCATION"
    )
    if not raw_location or raw_location == "global":
        location = os.environ.get("LOCATION", "us-central1")
    else:
        location = raw_location
    server_name = mcp_server_name or os.environ.get(
        "MCP_SERVER_NAME", "banking-mcp-server"
    )

    # Canonicalize MCP server resource path: projects/{proj}/locations/{loc}/mcpServers/{srv}
    if not server_name.startswith("projects/"):
        if not server_name.startswith("mcpServers/"):
            server_name = f"mcpServers/{server_name}"
        if project_id:
            server_name = f"projects/{project_id}/locations/{location}/{server_name}"

    registry = AgentRegistry(project_id=project_id, location=location)
    mcp_toolset = registry.get_mcp_toolset(server_name)
    return [mcp_toolset]


def get_banking_tools(
    mode: str = "auto",
    mcp_server_name: Optional[str] = None,
) -> List[Any]:
    """Resolve and return banking tools based on mode.

    Args:
        mode: 'auto', 'local', or 'registry'.
              - 'registry': connects to Google Cloud Agent Registry.
              - 'local': uses in-process FastMCP banking tools.
              - 'auto': uses Agent Registry if MCP_SERVER_NAME and GCP credentials exist,
                        otherwise falls back cleanly to local tools.
        mcp_server_name: Optional MCP server name or resource ID.

    Returns:
        List of tools (FunctionTools for local, McpToolset for registry).
    """
    if _should_use_registry(mode):
        try:
            logger.info("Resolving banking tools via Google Cloud Agent Registry...")
            return _get_registry_banking_tools(mcp_server_name=mcp_server_name)
        except Exception as e:
            if mode == "registry":
                raise RuntimeError(
                    f"Failed to load tools from Agent Registry in 'registry' mode: {e}"
                ) from e
            logger.warning(
                "Agent Registry resolution failed in 'auto' mode (%s). Falling back to local tools.",
                e,
            )
            return _get_local_banking_tools()

    logger.info("Using local banking tools (FunctionTool).")
    return _get_local_banking_tools()


def create_agent(
    mode: str = "auto",
    model: Optional[Union[str, BaseLlm]] = None,
    instruction: Optional[str] = None,
    name: str = "banking_agent",
    description: Optional[str] = None,
    tools: Optional[List[Any]] = None,
) -> Agent:
    """Create and configure an enterprise governed banking agent.

    Args:
        mode: Tool resolution mode ('auto', 'local', or 'registry'). Default 'auto'.
        model: Optional model instance or string identifier.
               Defaults to Gemini(model="gemini-3.8-flash", retry_options=HttpRetryOptions(attempts=3)).
        instruction: Optional system instruction override. Defaults to BANKING_INSTRUCTION.
        name: Name of the agent. Default 'banking_agent'.
        description: Description of the agent.
        tools: Optional explicit list of tools. If omitted, resolved via get_banking_tools(mode=mode).

    Returns:
        Configured ADK Agent instance.
    """
    if model is None:
        model = Gemini(
            model=os.environ.get("MODEL_ID", "gemini-3.8-flash"),
            retry_options=types.HttpRetryOptions(attempts=3),
        )

    resolved_tools = tools if tools is not None else get_banking_tools(mode=mode)
    resolved_instruction = (
        instruction if instruction is not None else BANKING_INSTRUCTION
    )
    resolved_description = (
        description
        or "Enterprise Governed Banking Assistant operating behind Google Cloud Agent Gateway"
    )

    return Agent(
        name=name,
        model=model,
        instruction=resolved_instruction,
        description=resolved_description,
        tools=resolved_tools,
    )


# Exported module-level defaults
root_agent: Agent = create_agent(mode="auto")
app: App = App(root_agent=root_agent, name="banking_app")
