"""Shared client + output helpers for the models/gemini/ demo scripts.

This is the hub of the cookbook: every demo (models.py, thinking.py, search.py, maps.py,
code_execution.py, url_context.py) imports its client, config, and print helpers from here, and
run.py orchestrates them. Importing this module also wires up three observability mechanisms, all
applied automatically to every demo request:

  1. Cloud Trace via OpenTelemetry  -- spans exported to GCP (set up at import time, below).
  2. Per-caller token attribution    -- `app`/`caller` labels on each request (default_labels).
  3. BigQuery request/response logs  -- enabled per-model when BIGQUERY_LOGGING_DESTINATION is set.

See models/gemini/README.md for the full walkthrough.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

load_dotenv(Path(__file__).parent / ".env")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
try:
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
except Exception:
    CloudTraceSpanExporter = None
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
provider = TracerProvider(resource=Resource.create({"service.name": "gemini-demos"}))
trace.set_tracer_provider(provider)

# 2. Set the global propagator to inject GCP-compatible and W3C-compatible trace headers into requests
set_global_textmap(CompositePropagator([
    TraceContextTextMapPropagator(),
    CloudTraceFormatPropagator()
]))

# 3. Export spans to GCP Cloud Trace (wrapped in try-except for robust fallback).
#    NOTE: these trace IDs are app-side only. Vertex AI does NOT copy them into Cloud Audit
#    Logs, so they CANNOT be used to join request/response logs with audit logs. Per-user
#    token attribution is done via request labels instead (see default_labels below).
_trace_proj = _trace_project()
try:
    if not CloudTraceSpanExporter:
        raise RuntimeError("CloudTraceSpanExporter unavailable")
    if not _trace_proj:
        raise RuntimeError("no project resolved (set GOOGLE_CLOUD_PROJECT or configure ADC)")
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter(project_id=_trace_proj))
    )
except Exception as e:
    print(f"Cloud Trace Exporter not initialized (local run fallback): {e}")

tracer = trace.get_tracer("gemini-demos")

try:
    from opentelemetry.instrumentation.google_genai import GoogleGenAiSdkInstrumentor
    GoogleGenAiSdkInstrumentor().instrument()
except Exception:
    pass

try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HTTPXClientInstrumentor().instrument()
except Exception:
    pass

try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    RequestsInstrumentor().instrument()
except Exception:
    pass

from google import genai
from google.genai import types



# Latest model per tier (prefer GA over preview). DEFAULT aliases one of these so demos can
# switch their default with a one-line change.
PRO = "gemini-3.1-pro-preview"
FLASH = "gemini-3.7-flash"
FLASH_LITE = "gemini-3.5-flash-lite"
GEMMA = "gemma-4-26b-a4b-it-maas"
DEFAULT = FLASH

console = Console()


# --- Per-caller token attribution via request labels -------------------------------------
# Vertex `generateContent` accepts a `labels` map (Google models only). Labels are written to
# `full_request.labels` in the request/response logging BigQuery table, which lets us attribute
# token usage to a caller WITHOUT joining the audit logs (the audit-log `trace` field is never
# populated by Vertex AI). Label values must match [a-z0-9_-]
# and be <= 63 chars; do not put PII (e.g. real user emails) in labels -- hash those instead.

_caller_label: str | None = None


def _sanitize_label_value(value: str) -> str:
    """Coerce a string into a valid Vertex label value: lowercase [a-z0-9_-], <= 63 chars."""
    sanitized = re.sub(r"[^a-z0-9_-]", "_", value.strip().lower())
    return sanitized[:63] or "unknown"


def _user_adc_email(creds) -> str | None:
    """Human principal email when ADC is user credentials (`gcloud auth application-default login`).

    Reads the email claim from the OIDC id_token that gcloud's ADC login returns (it grants the
    `openid` + `userinfo.email` scopes). This is a local JWT decode -- no network call and no API
    permissions required, so it works even where the userinfo endpoint is blocked by quota-project
    policy. Returns None for service-account ADC or when no verified email claim is present.
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
    """Best-effort IAM identity of the running process, sanitized for use as a label value.

    Resolution order: TOKEN_USAGE_LABEL override -> SA email from ADC creds -> user-ADC principal
    (id_token email claim) -> GCE metadata server -> "unknown". With user ADC the principal is
    resolved automatically, so no custom label is needed; set TOKEN_USAGE_LABEL only to override it
    (e.g. to attribute calls to an app-level end user -- hash the value first if it is PII). A blank
    or unset TOKEN_USAGE_LABEL is ignored and falls through to automatic resolution.
    """
    override = os.environ.get("TOKEN_USAGE_LABEL")
    if override:
        return _sanitize_label_value(override)

    creds = None
    try:
        import google.auth  # imported lazily: only needed when no explicit override is set

        creds, _ = google.auth.default(
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"]
        )
        email = getattr(creds, "service_account_email", None)
        if email and email != "default":
            return _sanitize_label_value(email)
    except Exception:
        pass

    # User ADC (gcloud auth application-default login): use the human principal. Must come BEFORE
    # the metadata-server fallback, which would otherwise return the host/workstation SA instead.
    if creds is not None:
        user_email = _user_adc_email(creds)
        if user_email:
            return _sanitize_label_value(user_email)

    # Compute/Cloud Shell ADC creds report service_account_email == "default" until the
    # metadata server is queried for the real address.
    try:
        from google.auth.compute_engine import _metadata
        from google.auth.transport.requests import Request

        info = _metadata.get_service_account_info(Request())
        email = info.get("email")
        if email:
            return _sanitize_label_value(email)
    except Exception:
        pass

    return "unknown"


def default_labels() -> dict[str, str]:
    """Labels attached to every demo request for per-caller token attribution."""
    global _caller_label
    if _caller_label is None:
        _caller_label = _resolve_caller()
    return {"app": "gemini-demos", "caller": _caller_label}


def labeled_config(config=None):
    """Return a GenerateContentConfig with `default_labels()` merged in.

    Pass an existing config to augment it (its own labels win on key collisions), or None to
    create a fresh config carrying only the default labels.
    """
    from google.genai import types  # imported lazily to keep this module cheap to import

    labels = default_labels()
    if config is None:
        return types.GenerateContentConfig(labels=labels)

    merged = dict(labels)
    merged.update(config.labels or {})
    config.labels = merged
    return config


def _configure_logging(project: str, location: str) -> None:
    """Enable Vertex request/response logging to BigQuery, once per (project, location, dest, models).

    No-op unless BIGQUERY_LOGGING_DESTINATION is set. Enabling logging is a per-model API call, so
    we record the applied configuration in a local `.logging_configured` cache file and skip the
    calls on subsequent runs when nothing changed. Delete that file to force a reconfigure.
    """
    bq_destination = os.environ.get("BIGQUERY_LOGGING_DESTINATION")
    if not bq_destination:
        return

    models = [PRO, FLASH, FLASH_LITE, GEMMA]
    cache_file = Path(__file__).parent / ".logging_configured"
    expected_content = f"{project}:{location}:{bq_destination}:{','.join(models)}"
    if cache_file.exists():
        try:
            if cache_file.read_text().strip() == expected_content:
                return
        except Exception:
            pass

    # Imported lazily: the aiplatform admin client is only needed when logging is enabled. We call
    # the EndpointServiceClient GAPIC directly rather than the deprecated vertexai GenerativeModel
    # SDK (removed 2026-06-24). "global" uses the unprefixed endpoint; regions are prefixed.
    from google.cloud.aiplatform_v1beta1 import EndpointServiceClient
    from google.cloud.aiplatform_v1beta1.types import (
        BigQueryDestination,
        PredictRequestResponseLoggingConfig,
        PublisherModelConfig,
        SetPublisherModelConfigRequest,
    )

    api_endpoint = (
        "aiplatform.googleapis.com"
        if location == "global"
        else f"{location}-aiplatform.googleapis.com"
    )
    client = EndpointServiceClient(client_options={"api_endpoint": api_endpoint})
    logging_config = PredictRequestResponseLoggingConfig(
        enabled=True,
        sampling_rate=1.0,
        bigquery_destination=BigQueryDestination(output_uri=f"bq://{bq_destination}"),
        enable_otel_logging=True,
    )
    for model_name in models:
        name = f"projects/{project}/locations/{location}/publishers/google/models/{model_name}"
        try:
            client.set_publisher_model_config(
                request=SetPublisherModelConfigRequest(
                    name=name,
                    publisher_model_config=PublisherModelConfig(logging_config=logging_config),
                )
            ).result()
        except Exception as e:
            # "already exists" just means the config is unchanged from a prior run; warn on anything else.
            if "already exists" not in str(e).lower():
                console.print(f"[yellow]Warning: Could not configure logging for {model_name}: {e}[/yellow]")

    try:
        cache_file.write_text(expected_content)
    except Exception:
        pass


def get_client() -> genai.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    if not project:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. "
            "Update models/gemini/.env with your project ID."
        )
    _configure_logging(project, location)
    return genai.Client(
        vertexai=True,
        project=project,
        location=location,
        http_options=types.HttpOptions(
            client_args={"verify": True},
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                max_delay=60.0,
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            ),
        ),
    )


def print_header(title: str) -> None:
    console.print()
    console.print(Panel(title, border_style="cyan", expand=False))


def print_response(label: str, response) -> None:
    console.print()
    console.rule(f"[bold cyan]{label}[/bold cyan]", style="cyan", align="left")
    text = getattr(response, "text", None)
    if text:
        console.print(Markdown(text.strip()))

    usage = getattr(response, "usage_metadata", None)
    _render_usage(usage)

    candidates = getattr(response, "candidates", None) or []
    if candidates:
        meta = getattr(candidates[0], "grounding_metadata", None)
        if meta:
            print_grounding(meta)

        url_meta = getattr(candidates[0], "url_context_metadata", None)
        if url_meta:
            console.print(f"[dim]url_context: {url_meta}[/dim]")


def print_grounding(meta) -> None:
    chunks = getattr(meta, "grounding_chunks", None) or []
    if not chunks:
        return
    console.print("[bold]Sources[/bold]")
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        maps_chunk = getattr(chunk, "maps", None)
        source = web or maps_chunk
        if not source:
            continue
        title = getattr(source, "title", "") or ""
        uri = getattr(source, "uri", "") or ""
        line = Text("  • ")
        if title:
            line.append(title)
        console.print(line)
        if uri:
            console.print(Text(f"    {uri}", style="blue underline"))


def print_code_block(code: str, language: str = "python") -> None:
    console.print()
    syntax = Syntax(
        code.rstrip(),
        language.lower(),
        theme="monokai",
        line_numbers=False,
        word_wrap=True,
    )
    console.print(
        Panel(syntax, title=f"executable_code ({language})", border_style="green", expand=False)
    )


def print_execution_result(outcome: str, output: str) -> None:
    console.print()
    console.rule(
        f"[bold green]code_execution_result ({outcome})[/bold green]",
        style="green",
        align="left",
    )
    console.print(Text(output.rstrip(), style="dim"))


def print_text(label: str, text: str) -> None:
    console.print()
    console.rule(f"[bold cyan]{label}[/bold cyan]", style="cyan", align="left")
    console.print(Markdown(text.strip()))


def _enum_name(value, default: str = "UNKNOWN") -> str:
    """Return the short name of a protobuf enum value (e.g. Language.PYTHON -> "PYTHON").

    Response parts carry enums that may arrive as a real enum object (has `.name`) or already as a
    string like "Language.PYTHON". This handles both: take `.name` if present, else str(), then
    keep the final dotted segment.
    """
    return getattr(value, "name", str(value)).split(".")[-1] or default


def _render_usage(usage) -> None:
    if not usage:
        return
    attrs = [("prompt", "prompt_token_count"), ("thoughts", "thoughts_token_count"),
             ("output", "candidates_token_count"), ("total", "total_token_count")]
    parts = [f"{k}={v}" for k, attr in attrs if (v := getattr(usage, attr, None)) is not None]
    if parts:
        console.print(f"[dim]tokens  {'  '.join(parts)}[/dim]")
