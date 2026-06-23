# Claude on Vertex AI cookbook

Small, self-contained demos of Anthropic Claude features on **Vertex AI** (via the
`anthropic[vertex]` SDK), in the same read-and-copy style as the sibling `models/gemini/` cookbook.
Each demo is one capability; the interesting part is one or two lines on `client.messages.*`, and the
rest is shared plumbing in `_common.py`.

Models are the latest of each tier only — `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`
— and non-model-specific demos default to **Sonnet** (`claude-sonnet-4-6`).

## What's here

| File | What it demonstrates |
| --- | --- |
| `models.py` | Run one prompt across the latest Opus, Sonnet, and Haiku. |
| `thinking.py` | Adaptive thinking at three effort tiers (`low`/`medium`/`high`) on one prompt. |
| `streaming.py` | Token-by-token streaming, then final usage via `get_final_message()`. |
| `tools.py` | Tool use (function calling) with a manual agentic loop + a local calculator tool. |
| `structured_outputs.py` | Typed extraction via `client.messages.parse()` into a Pydantic model. |
| `vision.py` | Image input (fetched at runtime and sent as base64). |
| `web_search.py` | Server-side web search grounding (Vertex's basic `web_search_20250305`). |
| `prompt_caching.py` | A large cached system prefix — written once, read cheaply next call. |
| `token_counting.py` | Exact model-specific input token count via `count_tokens`. |
| `_common.py` | Shared client, attribution, observability setup, rich console output. |
| `run.py` | Meta-runner: run one demo, several, or `all`. |
| `.env.example` | Template for the environment variables below. |

### How the files fit together

Every demo imports from `_common.py` and nothing else local — a simple hub-and-spoke:

```
                          run.py  (orchestrator)
                            │  calls <demo>.run()
   ┌───────┬────────┬───────┼────────┬───────────┬──────────────┬───────────────┐
models  thinking streaming tools structured  vision  web_search prompt_caching token_counting
   └───────┴────────┴───────┴───┬────┴───────────┴──────────────┴───────────────┘
                                │  import client + helpers
                           _common.py
                  (client, metadata, tracing, output)
```

Most demos share the same `run()` shape, so once you've read one you've read them all:

```python
print_header(...)                                          # rich banner
client = get_client()                                      # AnthropicVertex(project_id, region)
with tracer.start_as_current_span("vertex-prediction"):    # Cloud Trace span
    response = client.messages.create(
        model=DEFAULT,
        max_tokens=...,
        messages=[...],
        metadata=default_metadata(),                       # {"user_id": <resolved caller>}
        ...,                                               # the one capability arg
    )
print_response(label, response)                            # text/thinking blocks + token usage
```

A few demos diverge for good reason: `streaming.py` uses `client.messages.stream`, `tools.py` runs a
manual agentic loop, `structured_outputs.py` uses `client.messages.parse`, and `token_counting.py`
uses `client.messages.count_tokens`.

## Setup

```bash
uv sync                                                  # install dependencies (run from the repo root)
cp models/claude/.env.example models/claude/.env         # then fill in your values
gcloud auth application-default login                    # authenticate ADC (no Anthropic API key)
```

Environment variables (see `.env.example` for the authoritative list):

| Variable | Required? | Purpose |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | yes | GCP project for the `AnthropicVertex` client and Cloud Trace. |
| `GOOGLE_CLOUD_LOCATION` | yes | Vertex region — `global` (recommended), `us`/`eu`, or a specific region. |
| `ANTHROPIC_USER_ID` | optional | Attribute usage to an app-level end user via `metadata.user_id` (hash if PII). |

## Running the demos

```bash
uv run models/claude/run.py all                  # every demo
uv run models/claude/run.py models thinking      # named demos, in order
uv run models/claude/run.py tools
```

Each demo is also runnable on its own:

```bash
uv run models/claude/tools.py
```

## Observability — two layers

Importing `_common.py` wires both up automatically; every demo request flows through them.

### 1. Console (always on, zero setup)

The `print_*` helpers use [rich](https://rich.readthedocs.io/) to render each response: `thinking`
and `text` blocks, a `tokens input=… output=… [cache_write=… cache_read=…]` line read from
`response.usage`, and any web-search source URLs. This is the view you get locally with no GCP
configuration — the fastest way to *see* what each capability returns.

### 2. Cloud Trace (OpenTelemetry)

`_common.py` sets up tracing at import time:

- Registers a `TracerProvider` (service name `claude-demos`) so spans get real trace/span IDs.
- Installs a **composite propagator** (W3C `traceparent` + GCP `X-Cloud-Trace-Context`).
- Auto-instruments `httpx` (which the Anthropic SDK uses for the Vertex call) and `requests`, so HTTP
  calls are traced without per-call code.
- Exports spans to **Cloud Trace**. With no project/ADC available it prints a one-line fallback
  notice and keeps running — tracing just isn't exported.

Each demo wraps its API call in `tracer.start_as_current_span("vertex-prediction")`.

## Per-caller attribution (and why there's no BigQuery here)

The Messages API accepts a `metadata` object with a `user_id` string. `default_metadata()` stamps the
running process's resolved IAM identity into it on every request, so usage carries a caller in
**Anthropic-side** telemetry. `_resolve_caller()` resolves identity best-effort, in order:

1. `ANTHROPIC_USER_ID` env override (end-user attribution; hash any PII first),
2. service-account email from ADC,
3. the user principal under user ADC, decoded locally from the id_token's `email` claim,
4. the GCE metadata server (Compute Engine / Cloud Shell),
5. `unknown`.

Values are sanitized to `[a-z0-9_-]`, ≤63 chars.

> **Why no BigQuery request/response logging or label-SQL like the Gemini cookbook?** That scheme
> stamps `{app, caller}` into the Vertex `full_request.labels` map, which lands in a BigQuery logging
> table next to the token counts. The **Anthropic Messages API request body has no Vertex `labels`
> field**, and Vertex request/response logging for Anthropic publisher models is a different,
> unverified mechanism — so the label→BigQuery→SQL path does not carry over. Attribution here lives in
> `metadata.user_id` instead. See `../gemini/README.md` for the full Gemini attribution story.

## Vertex feature caveats

These demos deliberately stay within what Claude supports on Vertex AI. Notably **unsupported on
Vertex**: web *fetch*, code execution, the Batches and Files APIs, the MCP connector, managed agents,
mid-conversation `system` messages, and *automatic* prompt caching. Web *search* is the basic
`web_search_20250305` variant only (no `_20260209` dynamic filtering), and prompt caching must use
explicit `cache_control` blocks. Check feature availability before "upgrading" a demo.

## Customizing

To adapt a demo, change its `PROMPT` and the single capability argument on `messages.create(...)` —
e.g. the `tools=[...]` list, the `thinking`/`output_config` pair in `thinking.py`, or the
`output_format` model in `structured_outputs.py`. The client, tracing, attribution, and output
handling come from `_common.py` unchanged.
