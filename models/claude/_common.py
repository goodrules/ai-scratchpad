"""Shared client + output helpers for the models/claude/ demo scripts.

This is the hub of the Claude-on-Vertex cookbook: every demo imports its client, model aliases,
attribution metadata, and print helpers from here, and run.py orchestrates them. Importing this
module also wires up two observability mechanisms, applied to every demo request:

  1. Cloud Trace via OpenTelemetry  -- spans exported to GCP (set up at import time, below). The
     Anthropic SDK calls Vertex over httpx, so HTTPXClientInstrumentor traces the outbound call.
  2. Per-caller attribution           -- the resolved caller identity is stamped into the
     Anthropic-native `metadata.user_id` field on each request (default_metadata).

Unlike the Gemini cookbook there is NO BigQuery request/response logging or label-based SQL: the
Anthropic Messages API request body has no Vertex `labels` field, and Vertex request/response
logging for Anthropic publisher models is a different, unverified mechanism. See
models/claude/README.md for the rationale.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

load_dotenv(Path(__file__).parent / ".env")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def _trace_project() -> str | None:
    """Project for the Cloud Trace exporter: explicit env, else ADC default."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        return project
    try:
        import google.auth

        _, project = google.auth.default()
        return project
    except Exception:
        return None


# 1. Register the global Tracer Provider (forces generation of Trace/Span IDs)
provider = TracerProvider(resource=Resource.create({"service.name": "claude-demos"}))
trace.set_tracer_provider(provider)

# 2. Set the global propagator to inject GCP-compatible and W3C-compatible trace headers
set_global_textmap(CompositePropagator([
    TraceContextTextMapPropagator(),
    CloudTraceFormatPropagator(),
]))

# 3. Export spans to GCP Cloud Trace (wrapped in try-except for robust local fallback).
_trace_proj = _trace_project()
try:
    if not _trace_proj:
        raise RuntimeError("no project resolved (set GOOGLE_CLOUD_PROJECT or configure ADC)")
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter(project_id=_trace_proj))
    )
except Exception as e:
    print(f"Cloud Trace Exporter not initialized (local run fallback): {e}")

tracer = trace.get_tracer("claude-demos")

from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# The Anthropic SDK calls Vertex over httpx; instrument it (and requests, used by google-auth token
# refresh) so HTTP calls are traced and trace context is propagated without per-call code.
HTTPXClientInstrumentor().instrument()
RequestsInstrumentor().instrument()

from anthropic import AnthropicVertex


# Latest model per tier -- use only the latest Opus/Sonnet/Haiku. DEFAULT aliases one of these so
# non-model-specific demos switch their default with a one-line change.
OPUS = "claude-opus-5"
SONNET = "claude-sonnet-5"
HAIKU = "claude-haiku-4-5"
DEFAULT = SONNET

console = Console()


# --- Per-caller attribution via Anthropic metadata.user_id -------------------------------------
# The Messages API accepts a `metadata` object with a `user_id` string. We stamp the running
# process's resolved IAM identity there so each request carries a caller in Anthropic-side
# telemetry. This is the Anthropic-native analog of the Gemini cookbook's request `labels` -- there
# is no Vertex `labels` field on the Anthropic request, so the BigQuery label-join scheme does not
# apply. Anthropic recommends an opaque user_id; hash any PII before using it.

_caller: str | None = None


def _sanitize_user_id(value: str) -> str:
    """Coerce a string into a compact opaque id: lowercase [a-z0-9_-], <= 63 chars."""
    sanitized = re.sub(r"[^a-z0-9_-]", "_", value.strip().lower())
    return sanitized[:63] or "unknown"


def _user_adc_email(creds) -> str | None:
    """Human principal email when ADC is user credentials (`gcloud auth application-default login`).

    Reads the email claim from the OIDC id_token gcloud's ADC login returns (it grants `openid` +
    `userinfo.email`). This is a local JWT decode -- no network call and no API permissions -- so it
    works even where the userinfo endpoint is blocked. Returns None for service-account ADC or when
    no verified email claim is present.
    """
    try:
        import base64
        import json

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials as UserCredentials

        if not isinstance(creds, UserCredentials):
            return None  # service-account ADC: handled by the service_account_email path
        creds.refresh(Request())
        id_token = getattr(creds, "id_token", None)
        if not id_token:
            return None
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # restore base64url padding
        claims = json.loads(base64.urlsafe_b64decode(payload))
        if claims.get("email_verified") and claims.get("email"):
            return claims["email"]
    except Exception:
        return None
    return None


def _resolve_caller() -> str:
    """Best-effort IAM identity of the running process, sanitized for use as a user_id.

    Resolution order: ANTHROPIC_USER_ID override -> SA email from ADC creds -> user-ADC principal
    (id_token email claim) -> GCE metadata server -> "unknown". With user ADC the principal is
    resolved automatically; set ANTHROPIC_USER_ID only to override it (e.g. to attribute calls to an
    app-level end user -- hash the value first if it is PII).
    """
    override = os.environ.get("ANTHROPIC_USER_ID")
    if override:
        return _sanitize_user_id(override)

    creds = None
    try:
        import google.auth  # imported lazily: only needed when no explicit override is set

        creds, _ = google.auth.default(
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"]
        )
        email = getattr(creds, "service_account_email", None)
        if email and email != "default":
            return _sanitize_user_id(email)
    except Exception:
        pass

    # User ADC (gcloud auth application-default login): use the human principal. Must come BEFORE the
    # metadata-server fallback, which would otherwise return the host/workstation SA instead.
    if creds is not None:
        user_email = _user_adc_email(creds)
        if user_email:
            return _sanitize_user_id(user_email)

    # Compute/Cloud Shell ADC creds report service_account_email == "default" until the metadata
    # server is queried for the real address.
    try:
        from google.auth.compute_engine import _metadata
        from google.auth.transport.requests import Request

        info = _metadata.get_service_account_info(Request())
        email = info.get("email")
        if email:
            return _sanitize_user_id(email)
    except Exception:
        pass

    return "unknown"


def default_metadata() -> dict[str, str]:
    """Anthropic `metadata` attached to every demo request for per-caller attribution."""
    global _caller
    if _caller is None:
        _caller = _resolve_caller()
    return {"user_id": _caller}


def get_client() -> AnthropicVertex:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    if not project or not location:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION is not set. "
            "Update models/claude/.env with your project ID and location (region)."
        )
    # Auth is GCP ADC (gcloud auth application-default login); no Anthropic API key. `region` may be
    # "global" (recommended), a multi-region ("us"/"eu"), or a specific region.
    return AnthropicVertex(project_id=project, region=location)


# --- Output helpers ----------------------------------------------------------------------------

def print_header(title: str) -> None:
    console.print()
    console.print(Panel(title, border_style="cyan", expand=False))


def print_response(label: str, response) -> None:
    """Render an Anthropic Message: thinking + text blocks, a token-usage line, web-search sources."""
    console.print()
    console.rule(f"[bold cyan]{label}[/bold cyan]", style="cyan", align="left")
    for block in getattr(response, "content", None) or []:
        btype = getattr(block, "type", None)
        if btype == "thinking":
            thinking = (getattr(block, "thinking", "") or "").strip()
            if thinking:
                console.print(f"[dim italic]{thinking}[/dim italic]")
        elif btype == "text":
            text = (getattr(block, "text", "") or "").strip()
            if text:
                console.print(Markdown(text))
    _render_usage(getattr(response, "usage", None))
    print_citations(response)


def print_citations(response) -> None:
    """Print any web-search source URLs referenced in the response, deduped."""
    blocks = [b.content for b in getattr(response, "content", None) or []
              if getattr(b, "type", None) == "web_search_tool_result" and isinstance(getattr(b, "content", None), list)]
    sources = {getattr(r, "url", ""): getattr(r, "title", "") for chunk in blocks for r in chunk if getattr(r, "url", "")}
    if not sources:
        return
    console.print("[bold]Sources[/bold]")
    for url, title in sources.items():
        line = Text("  • ")
        if title:
            line.append(title)
        console.print(line)
        console.print(Text(f"    {url}", style="blue underline"))


def _render_usage(usage) -> None:
    if not usage:
        return
    attrs = [("input", "input_tokens"), ("output", "output_tokens"),
             ("cache_write", "cache_creation_input_tokens"), ("cache_read", "cache_read_input_tokens")]
    parts = [f"{k}={v}" for k, attr in attrs if (v := getattr(usage, attr, None))]
    if parts:
        console.print(f"[dim]tokens  {'  '.join(parts)}[/dim]")
