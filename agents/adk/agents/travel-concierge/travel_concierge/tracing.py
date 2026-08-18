"""Native Google Cloud Trace & OpenTelemetry tracing setup for Travel Concierge."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

load_dotenv(Path(__file__).parents[1] / ".env")


def setup_telemetry() -> trace.Tracer:
    """Initialize native GCP Cloud Trace OpenTelemetry provider with fallback."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        try:
            import google.auth

            _, project = google.auth.default()
        except Exception:
            project = None

    provider = TracerProvider(
        resource=Resource.create({"service.name": "travel-concierge-agent"})
    )
    trace.set_tracer_provider(provider)

    set_global_textmap(
        CompositePropagator([
            TraceContextTextMapPropagator(),
            CloudTraceFormatPropagator(),
        ])
    )

    try:
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

        if project:
            provider.add_span_processor(
                BatchSpanProcessor(CloudTraceSpanExporter(project_id=project))
            )
    except Exception:
        pass

    return trace.get_tracer("travel-concierge-agent")

