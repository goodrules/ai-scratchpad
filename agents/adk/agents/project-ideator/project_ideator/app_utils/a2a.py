# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Attach A2A (Agent2Agent) endpoints to the FastAPI app.

func:`attach_a2a_routes` registers the dynamic
agent-card endpoint and the JSON-RPC endpoint so the same app serves A2A
alongside the adk_api routes, reachable by A2A clients and Gemini Enterprise A2A
registration.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import TaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentExtension,
    AgentInterface,
    Message,
    TaskStatusUpdateEvent,
)
from a2a.server.events import Event as A2AEvent
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a import _compat
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.executor.config import (
    A2aAgentExecutorConfig,
    ExecuteInterceptor,
)
from google.adk.a2a.executor.executor_context import ExecutorContext
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.events import Event

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from google.adk.agents import BaseAgent
    from google.adk.runners import Runner

# URI advertised on the agent card describing the executor extension shipped
# by ADK. Kept as a module-level constant so callers can override or extend
# the capabilities list when needed.
_ADK_AGENT_EXECUTOR_EXTENSION_URI = (
    "https://google.github.io/adk-docs/a2a/a2a-extension/"
)


async def _add_v0_3_compat_interface(card: AgentCard) -> AgentCard:
    """Advertise a v0.3 JSON-RPC interface so the served card stays consumable by
    v0.3 A2A clients — notably Gemini Enterprise registration, whose validator
    still requires the 0.3 card shape (top-level ``url``/``protocolVersion``)."""
    if card.supported_interfaces:
        card.supported_interfaces.append(
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="0.3",
                url=card.supported_interfaces[0].url,
            )
        )
    return card


def _default_capabilities() -> AgentCapabilities:
    """Returns the default A2A capabilities used by scaffolded projects."""
    return AgentCapabilities(
        streaming=False,
        extensions=[
            AgentExtension(
                uri="https://a2ui.org/a2a-extension/a2ui/v0.8",
                description="A2UI v0.8 interactive UI extension",
                params={
                    "supportedCatalogIds": [
                        "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
                    ]
                },
                required=False,
            ),
            AgentExtension(
                uri=_ADK_AGENT_EXECUTOR_EXTENSION_URI,
                description=("Ability to use the new agent executor implementation"),
            ),
        ],
    )


_A2UI_UPDATE_TYPES = (
    "beginRendering",
    "surfaceUpdate",
    "dataModelUpdate",
    "createSurface",
    "updateComponents",
    "updateDataModel",
    "deleteSurface",
)


def _clean_and_parse_json(raw: str) -> list[dict[str, Any]] | None:
    """Parse a raw JSON string into a list of dicts, tolerating Markdown formatting."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
        elif isinstance(data, dict):
            return [data]
    except Exception as e:
        logger.debug("Failed to parse A2UI JSON payload: %s", e)
    return None


def _extract_a2ui_messages_from_text(
    text: str,
) -> tuple[str, list[dict[str, Any]], str] | None:
    """Extract embedded A2UI JSON array from response text."""
    if not text:
        return None

    # 1. Look for <a2ui-json>...</a2ui-json>
    tag_match = re.search(r"<a2ui-json>\s*(.*?)\s*</a2ui-json>", text, re.DOTALL)
    if tag_match:
        messages = _clean_and_parse_json(tag_match.group(1))
        if messages:
            return (
                text[: tag_match.start()].strip(),
                messages,
                text[tag_match.end() :].strip(),
            )

    # 2. Look for ```json [...] ```
    for m in re.finditer(r"```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```", text, re.DOTALL):
        messages = _clean_and_parse_json(m.group(1))
        if messages:
            return text[: m.start()].strip(), messages, text[m.end() :].strip()

    # 3. Raw JSON array [ ... ]
    raw_match = re.search(r"(\[\s*\{.*\}\s*\])", text, re.DOTALL)
    if raw_match:
        messages = _clean_and_parse_json(raw_match.group(1))
        if messages:
            return (
                text[: raw_match.start()].strip(),
                messages,
                text[raw_match.end() :].strip(),
            )

    return None


def _remap_surface_ids(data: Any, surface_id_map: dict[str, str]) -> Any:
    """Consistently remap surface IDs in A2UI messages for a turn."""
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if k in _A2UI_UPDATE_TYPES:
                if isinstance(v, dict) and "surfaceId" in v:
                    orig_sid = v["surfaceId"]
                    if orig_sid not in surface_id_map:
                        slug = re.sub(r"[^a-zA-Z0-9_-]", "", str(orig_sid)) or "surface"
                        surface_id_map[orig_sid] = f"{slug}-{uuid.uuid4().hex[:6]}"
                    v = {**v, "surfaceId": surface_id_map[orig_sid]}
            new_dict[k] = _remap_surface_ids(v, surface_id_map)
        return new_dict
    elif isinstance(data, list):
        return [_remap_surface_ids(item, surface_id_map) for item in data]
    return data


def _split_combined_a2ui_data(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Split combined A2UI messages into separate compliant messages."""
    types_present = [t for t in _A2UI_UPDATE_TYPES if t in data]
    if len(types_present) <= 1:
        return [data]
    base = {"version": data["version"]} if "version" in data else {}
    return [{**base, t: data[t]} for t in types_present]


def _deduplicate_a2ui_parts(parts: list[Any]) -> list[Any]:
    """Deduplicate A2UI data parts so each message type per surface appears at most once."""
    seen_keys: set[tuple[str, str]] = set()
    deduped: list[Any] = []
    for p in parts:
        if _compat.is_data_part(p):
            d = _compat.data_part_dict(p)
            if isinstance(d, dict):
                msg_type = next((k for k in _A2UI_UPDATE_TYPES if k in d), None)
                if msg_type:
                    surface_id = d[msg_type].get("surfaceId", "")
                    key = (surface_id, msg_type)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
        deduped.append(p)
    return deduped


def _process_parts(parts: list[Any], executor_context: ExecutorContext) -> list[Any]:
    """Process parts list, converting any A2UI text/data into proper DataParts with clean text."""
    surface_id_map: dict[str, str] = getattr(executor_context, "_surface_id_map", {})
    setattr(executor_context, "_surface_id_map", surface_id_map)
    new_parts: list[Any] = []
    a2ui_parts: list[Any] = list(getattr(executor_context, "_last_a2ui_parts", []))
    collected_clean_text = getattr(executor_context, "_clean_text", "")

    for part in parts:
        if _compat.is_text_part(part):
            text = _compat.part_text(part) or ""
            extracted = _extract_a2ui_messages_from_text(text)
            pending_tool_msgs = getattr(executor_context, "_pending_tool_a2ui_messages", None)

            if extracted is not None:
                prefix_text, messages, suffix_text = extracted
                clean_text = " ".join(filter(None, [prefix_text, suffix_text])).strip()
                if clean_text:
                    new_parts.append(_compat.make_text_part(clean_text))
                    collected_clean_text = clean_text
                # Clear pending tool messages since the text explicitly carried the payload
                setattr(executor_context, "_pending_tool_a2ui_messages", None)
                for msg in messages:
                    for split_msg in _split_combined_a2ui_data(msg):
                        remapped = _remap_surface_ids(split_msg, surface_id_map)
                        dp = _compat.make_data_part(
                            data=remapped,
                            metadata={"mimeType": "application/json+a2ui"},
                        )
                        new_parts.append(dp)
                        a2ui_parts.append(dp)
            elif pending_tool_msgs:
                # Text did not contain raw <a2ui-json>, attach pending tool A2UI messages to this text
                if text:
                    new_parts.append(part)
                    collected_clean_text = text
                setattr(executor_context, "_pending_tool_a2ui_messages", None)
                for msg in pending_tool_msgs:
                    for split_msg in _split_combined_a2ui_data(msg):
                        remapped = _remap_surface_ids(split_msg, surface_id_map)
                        dp = _compat.make_data_part(
                            data=remapped,
                            metadata={"mimeType": "application/json+a2ui"},
                        )
                        new_parts.append(dp)
                        a2ui_parts.append(dp)
            else:
                new_parts.append(part)
                if not collected_clean_text and text:
                    collected_clean_text = text
        elif _compat.is_data_part(part):
            data = _compat.data_part_dict(part)
            if isinstance(data, dict):
                # 1. Unpack function responses containing a2ui_payload or validated_a2ui_json
                resp = data.get("response", {}) if "response" in data else data
                payload_candidates = []
                if isinstance(resp, dict):
                    if "a2ui_payload" in resp and isinstance(resp["a2ui_payload"], dict):
                        msgs = resp["a2ui_payload"].get("a2ui_messages", [])
                        if isinstance(msgs, list):
                            payload_candidates.extend(msgs)
                    if "validated_a2ui_json" in resp and isinstance(resp["validated_a2ui_json"], list):
                        payload_candidates.extend(resp["validated_a2ui_json"])

                if payload_candidates:
                    # Stash tool A2UI messages for attachment to the subsequent model text message.
                    # DO NOT replace function response with A2UI DataParts in this intermediate artifact,
                    # because doing so causes Gemini Enterprise to display a duplicate/phantom card
                    # before the conversational text.
                    setattr(executor_context, "_pending_tool_a2ui_messages", payload_candidates)
                    new_parts.append(part)
                    continue

                # 2. Already an A2UI DataPart
                metadata = getattr(part, "metadata", {}) or {}
                mime = metadata.get("mimeType") if isinstance(metadata, dict) else None
                if mime in ("application/json+a2ui", "application/a2ui+json"):
                    remapped = _remap_surface_ids(data, surface_id_map)
                    dp = _compat.make_data_part(
                        data=remapped,
                        metadata={"mimeType": "application/json+a2ui"},
                    )
                    new_parts.append(dp)
                    a2ui_parts.append(dp)
                    continue

            new_parts.append(part)
        else:
            new_parts.append(part)

    a2ui_parts = _deduplicate_a2ui_parts(a2ui_parts)
    setattr(executor_context, "_clean_text", collected_clean_text)
    setattr(executor_context, "_last_a2ui_parts", a2ui_parts)
    return _deduplicate_a2ui_parts(new_parts)


def _create_a2ui_interceptor() -> ExecuteInterceptor:
    async def before_agent(request_context: RequestContext) -> RequestContext:
        if not request_context.message:
            return request_context
        for part in list(request_context.message.parts):
            if _compat.is_data_part(part):
                data = _compat.data_part_dict(part)
                if "userAction" in data:
                    action = data.get("userAction", {})
                    name = action.get("name", "")
                    raw_ctx = action.get("context", {})

                    # Normalize context whether received as list or dict
                    ctx: dict[str, Any] = {}
                    if isinstance(raw_ctx, list):
                        for item in raw_ctx:
                            if isinstance(item, dict) and "key" in item:
                                val = item.get("value")
                                if isinstance(val, dict):
                                    val = (
                                        val.get("literalString")
                                        or val.get("literalNumber")
                                        or val.get("literalBoolean")
                                        or str(val)
                                    )
                                ctx[item["key"]] = val
                    elif isinstance(raw_ctx, dict):
                        for k, v in raw_ctx.items():
                            if isinstance(v, dict):
                                v = (
                                    v.get("literalString")
                                    or v.get("literalNumber")
                                    or v.get("literalBoolean")
                                    or str(v)
                                )
                            ctx[k] = v

                    if name == "select_stage_option":
                        stage = ctx.get("stage", "")
                        opt = ctx.get("selected_option", "")
                        text = f"Selected option for {stage}: {opt}"
                    elif name == "submit_stage_input":
                        stage = ctx.get("stage", "")
                        custom = ctx.get("custom_text") or ctx.get("value") or ""
                        text = (
                            f"Custom input for {stage}: {custom}"
                            if custom
                            else f"Advance stage: {stage}"
                        )
                    elif name == "export_prd_file":
                        fn = ctx.get("filename", "PRD.md")
                        text = f"Please export and save the PRD as {fn}."
                    elif name == "revise_stage":
                        stage = ctx.get("stage", "problem_and_goal")
                        text = f"Let's revise the project from {stage}."
                    elif name == "reset_session":
                        text = "Let's start ideating a new project."
                    else:
                        text = f"Action: {name} with data: {ctx}"
                    request_context.message.parts.append(
                        _compat.make_text_part(text)
                    )
        return request_context

    async def after_event(
        executor_context: ExecutorContext,
        a2a_event: A2AEvent,
        adk_event: Event,
    ) -> A2AEvent:
        # 1. Handle TaskArtifactUpdateEvent (where ADK places model output parts)
        artifact = getattr(a2a_event, "artifact", None)
        if artifact and getattr(artifact, "parts", None):
            new_parts = _process_parts(list(artifact.parts), executor_context)
            del artifact.parts[:]
            artifact.parts.extend(new_parts)

        # 2. Handle TaskStatusUpdateEvent message if present
        status = getattr(a2a_event, "status", None)
        msg = getattr(status, "message", None)
        if msg and getattr(msg, "parts", None):
            new_parts = _process_parts(list(msg.parts), executor_context)
            del msg.parts[:]
            msg.parts.extend(new_parts)

        return a2a_event

    async def after_agent(
        executor_context: ExecutorContext,
        final_event: TaskStatusUpdateEvent,
    ) -> TaskStatusUpdateEvent:
        final_event.status.state = _compat.TS_COMPLETED
        last_a2ui_parts = _deduplicate_a2ui_parts(
            getattr(executor_context, "_last_a2ui_parts", [])
        )
        clean_text = getattr(executor_context, "_clean_text", "")

        # Fallback if no text event consumed pending tool messages
        pending_tool_msgs = getattr(executor_context, "_pending_tool_a2ui_messages", None)
        if pending_tool_msgs and not last_a2ui_parts:
            surface_id_map: dict[str, str] = getattr(executor_context, "_surface_id_map", {})
            for msg in pending_tool_msgs:
                for split_msg in _split_combined_a2ui_data(msg):
                    remapped = _remap_surface_ids(split_msg, surface_id_map)
                    dp = _compat.make_data_part(
                        data=remapped,
                        metadata={"mimeType": "application/json+a2ui"},
                    )
                    last_a2ui_parts.append(dp)
            setattr(executor_context, "_pending_tool_a2ui_messages", None)

        last_a2ui_parts = _deduplicate_a2ui_parts(last_a2ui_parts)

        msg = getattr(getattr(final_event, "status", None), "message", None)
        if msg and getattr(msg, "parts", None):
            deduped = _deduplicate_a2ui_parts(list(msg.parts))
            del msg.parts[:]
            msg.parts.extend(deduped)
        else:
            parts = []
            if clean_text:
                parts.append(_compat.make_text_part(clean_text))
            if last_a2ui_parts:
                parts.extend(last_a2ui_parts)
            if parts:
                final_msg = Message(
                    role=_compat.ROLE_AGENT,
                    parts=parts,
                )
                final_event.status.message.CopyFrom(final_msg)
        return final_event

    return ExecuteInterceptor(
        before_agent=before_agent,
        after_event=after_event,
        after_agent=after_agent,
    )


def _resolve_app_url(app_url: str | None) -> str:
    """Resolve the public base URL advertised inside the agent card.

    Falls back in order: explicit ``app_url``, the ``APP_URL`` env var, the
    Agent Runtime ``/api`` passthrough self-built from runtime env vars (valid
    on the first deploy, before the CLI knows the server-assigned engine ID),
    then a local default.
    """
    if app_url:
        return app_url
    if env_url := os.getenv("APP_URL"):
        return env_url

    agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    # Not GOOGLE_CLOUD_LOCATION: the agent pins it to "global", which would build
    # an invalid "global-aiplatform.googleapis.com" URL.
    location = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION", "us-east1")
    if agent_engine_id and project and location:
        return (
            f"https://{location}-aiplatform.googleapis.com/reasoningEngines/v1"
            f"/projects/{project}/locations/{location}"
            f"/reasoningEngines/{agent_engine_id}/api"
        )

    return "http://0.0.0.0:8000"


async def attach_a2a_routes(
    app: FastAPI,
    *,
    agent: BaseAgent,
    runner: Runner,
    task_store: TaskStore,
    rpc_path: str,
    capabilities: AgentCapabilities | None = None,
    agent_version: str | None = None,
    app_url: str | None = None,
) -> None:
    """Register A2A routes (JSON-RPC + agent-card endpoints) under ``rpc_path``.

    Builds a dynamic agent card from ``agent`` and mounts the routes on ``app``.
    The ``runner`` should share the session/artifact/memory services with the
    standard ADK path. ``capabilities``, ``agent_version``, and ``app_url``
    override their defaults (streaming + ADK extension, ``AGENT_VERSION``,
    ``APP_URL``). Call once per app — typically in a FastAPI ``lifespan``, since
    the card is built asynchronously; repeated calls register duplicate routes.
    """
    resolved_app_url = _resolve_app_url(app_url)
    resolved_agent_version = agent_version or os.getenv("AGENT_VERSION", "0.1.0")
    resolved_capabilities = capabilities or _default_capabilities()

    agent_card = await AgentCardBuilder(
        agent=agent,
        capabilities=resolved_capabilities,
        rpc_url=f"{resolved_app_url}{rpc_path}",
        agent_version=resolved_agent_version,
    ).build()

    request_handler = DefaultRequestHandler(
        agent_executor=A2aAgentExecutor(
            runner=runner,
            force_new_version=True,
            config=A2aAgentExecutorConfig(
                execute_interceptors=[_create_a2ui_interceptor()]
            ),
        ),
        task_store=task_store,
        agent_card=agent_card,
    )

    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(
            agent_card,
            card_modifier=_add_v0_3_compat_interface,
            card_url=f"{rpc_path}{AGENT_CARD_WELL_KNOWN_PATH}",
        ),
        jsonrpc_routes=create_jsonrpc_routes(
            request_handler,
            rpc_url=rpc_path,
            enable_v0_3_compat=True,
        ),
    )
