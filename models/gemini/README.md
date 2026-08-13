# Gemini 3/3.5 cookbook

Small, self-contained demos of Gemini 3/3.5 features on Vertex AI, plus the observability wiring
(Cloud Trace, BigQuery request/response logging, per-caller token attribution) and the SQL to
report on it. Each demo is meant to be **read and copied** — the interesting part is one or two
lines of config; the rest is shared plumbing in `_common.py`.

Models are the latest of each tier only — Gemini Pro (`gemini-3.1-pro-preview`), Gemini Flash (`gemini-3.7-flash`), and Gemini Flash-Lite (`gemini-3.5-flash-lite`) — and non-model-specific demos default to **Flash** (`gemini-3.7-flash`).

## What's here

| File | What it demonstrates |
| --- | --- |
| `models.py` | Run one prompt across every Gemini 3/3.5 model. |
| `thinking.py` | The four thinking tiers (`minimal`/`low`/`medium`/`high`) on one prompt. |
| `search.py` | Google Search grounding (answers from live web results). |
| `url_context.py` | URL Context tool (model fetches and reads URLs in the prompt). |
| `maps.py` | Google Maps grounding, anchored at coordinates resolved via structured output. |
| `code_execution.py` | Code execution: model writes Python, the platform runs it, result returned. |
| `_common.py` | Shared client, config helpers, observability setup, rich console output. |
| `run.py` | Meta-runner: run one demo, a named group, or all of them. |
| `sql/` | BigQuery queries for per-caller / per-principal token usage. |
| `.env.example` | Template for the environment variables below. |

### How the files fit together

Every demo imports from `_common.py` and nothing else local — a simple hub-and-spoke:

```
                      run.py  (orchestrator)
                        │  calls <demo>.run()
   ┌──────────┬─────────┼─────────┬──────────────┬─────────────┐
models.py  thinking.py  search.py  url_context.py  maps.py  code_execution.py
   └──────────┴─────────┴────┬────┴──────────────┴─────────────┘
                             │  import client + helpers
                        _common.py
                  (client, labels, tracing, logging, output)
```

Each demo's `run()` follows the same shape, so once you've read one you've read them all:

```python
print_header(...)                                   # rich banner
client = get_client()                               # configured genai.Client (+ logging setup)
with tracer.start_as_current_span("vertex-prediction"):   # Cloud Trace span
    response = client.models.generate_content(
        model=DEFAULT,
        contents=PROMPT,
        config=labeled_config(...),                 # merges per-caller attribution labels
    )
print_response(label, response)                     # text + token usage + grounding sources
```

## Setup

```bash
uv sync                                                  # install dependencies (run from the repo root)
cp models/gemini/.env.example models/gemini/.env         # then fill in your values
gcloud auth application-default login                    # authenticate ADC
```

Environment variables (see `.env.example` for the authoritative list):

| Variable | Required? | Purpose |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | yes | Project for the Vertex client, Cloud Trace, and logging. |
| `GOOGLE_CLOUD_LOCATION` | yes | Vertex location (e.g. `global`). |
| `BIGQUERY_LOGGING_DESTINATION` | optional | `project.dataset.table` to enable request/response logging. |
| `TOKEN_USAGE_LABEL` | optional | Attribute usage to an app-level end user (hash if PII). |
| `GOOGLE_CLOUD_API_KEY` | optional | API key as an alternative to ADC. |

## Running the demos

```bash
uv run models/gemini/run.py all           # every demo
uv run models/gemini/run.py tools         # search, maps, code_execution, url_context
uv run models/gemini/run.py search maps   # named demos, in order
uv run models/gemini/run.py thinking
```

Each demo is also runnable on its own:

```bash
uv run models/gemini/search.py
```

## Observability — three layers

Importing `_common.py` wires all three up automatically; every demo request flows through them.

### 1. Console (always on, zero setup)

The `print_*` helpers in `_common.py` use [rich](https://rich.readthedocs.io/) to render the
response text, a `tokens prompt=… thoughts=… output=… total=…` line, and any grounding sources
(web/maps) or URL-context metadata. This is the view you get locally with no GCP logging
configured — the fastest way to *see* what each capability returns.

### 2. Cloud Trace (OpenTelemetry)

`_common.py` sets up tracing at import time:

- Registers a `TracerProvider` (service name `gemini-demos`) so spans get real trace/span IDs.
- Installs a **composite propagator** (W3C `traceparent` + GCP `X-Cloud-Trace-Context`) so trace
  context is injected into outgoing requests in both formats.
- Auto-instruments the Google Gen AI SDK, `httpx`, and `requests`, so HTTP calls are traced
  without per-call code.
- Exports spans to **Cloud Trace**. If no project/ADC is available it prints a one-line fallback
  notice and keeps running (handy for local experiments) — tracing just isn't exported.

Each demo wraps its API call in `tracer.start_as_current_span("vertex-prediction")` so the
prediction shows up as a named span.

> **Important limitation:** these trace IDs are *app-side only*. Vertex AI does **not** copy them
> into Cloud Audit Logs, so you cannot join request/response logs to audit logs on trace ID. That's
> why per-caller token attribution uses **request labels** instead (next section).

### 3. BigQuery request/response logging

Set `BIGQUERY_LOGGING_DESTINATION` to `project.dataset.table` and `get_client()` will call
`_configure_logging()`, which enables Vertex request/response logging for each demo model with
`sampling_rate=1.0` and `enable_otel_logging=True`. Full requests and responses (including the
`labels` map and `usageMetadata` token counts) land in that BigQuery table.

Enabling logging is a per-model API call, so the applied configuration is recorded in a local
`.logging_configured` cache file and skipped on later runs when nothing changed. Delete that file
to force a reconfigure. (It contains project/dataset identifiers and is git-ignored.)

## Per-caller token attribution

`generateContent` accepts a `labels` map (Google models only) that Vertex writes to
`full_request.labels` in the logging table — so you can attribute token usage to a caller **without
joining the audit logs**. `default_labels()` attaches two labels to every request via
`labeled_config()`:

- `app` — always `gemini-demos`.
- `caller` — resolved best-effort, in order:
  1. `TOKEN_USAGE_LABEL` env override (use for end-user attribution; hash any PII first),
  2. service-account email from ADC,
  3. the user principal under user ADC (`gcloud auth application-default login`), decoded locally
     from the id_token's `email` claim — no network call, no extra API permissions,
  4. the GCE metadata server (Compute Engine / Cloud Shell),
  5. `unknown`.

  Step 3 means a developer running on their own ADC is attributed to *their* principal
  automatically, not the host/workstation service account — without setting any label.

Label values are sanitized to `[a-z0-9_-]`, ≤63 chars. **Never put PII (e.g. real emails) in
labels** — hash them.

## The SQL queries

Both live in `sql/` and read the BigQuery table from `BIGQUERY_LOGGING_DESTINATION`. Replace the
`<PROJECT_ID>.<DATASET>.<LOGGING_TABLE>` placeholders (they map to `GOOGLE_CLOUD_PROJECT` and
`BIGQUERY_LOGGING_DESTINATION`) and run with `bq`:

```bash
bq query --use_legacy_sql=false --project_id=<PROJECT_ID> < models/gemini/sql/usage_by_caller.sql
```

| Query | Method | When to use |
| --- | --- | --- |
| `usage_by_caller.sql` | **Primary, exact.** Groups token usage by the `caller`/`app` labels read straight from `full_request.labels`. No join. | The default. Works for any row logged *after* labels were enabled. |
| `usage_audit_join.sql` | **Secondary, fuzzy.** Joins request/response logs to Cloud Audit Logs on `(model + timestamp)` to attribute usage to the IAM `principalEmail`. | Rows logged *before* labels existed, or when you need the GCP principal rather than an app label. |

### Why you can't cleanly join the two tables

The principal (`principalEmail`) lives only in Cloud Audit Logs; the token counts live only in the
request/response (RR) table. Joining them would solve "tokens by user" — but Vertex AI exposes **no
shared key** between them. Every candidate field falls down:

| Field | Audit log (has principal) | RR table (has tokens) | Usable join key? |
| --- | --- | --- | --- |
| `principalEmail` | ✅ present | ❌ absent | — |
| token counts (`usageMetadata`) | ❌ absent | ✅ present | — |
| `request_id` (NUMERIC) | ❌ no counterpart | ✅ present | no |
| `operation.id` | empty for `GenerateContent` | n/a | no |
| `metadata` / `otel_log` | n/a | latency + prompt content only, **no identity** | no |
| `full_request.labels` | ❌ not in audit payload | ✅ `{app, caller}` | — |
| trace / span ID | ❌ never populated by Vertex | app-side only | no |

That leaves **model + timestamp** as the only overlap — which is exactly what `usage_audit_join.sql`
uses, and why it's fuzzy: it's reliable only at low/sequential volume, since two principals calling
the same model inside the match window are indistinguishable. (And audit logs carry no token counts
anyway, so even a perfect join still needs the RR table for the numbers.)

**This is the whole reason for the label approach.** Stamping the caller into `full_request.labels`
puts identity in the same RR row as the tokens, so `usage_by_caller.sql` is an exact `GROUP BY` with
no join. Prefer it whenever possible.

## Customizing

To adapt a demo, change its `PROMPT` and the single config line that selects the capability — e.g.
the `tools=[...]` entry in `search.py`/`url_context.py`/`maps.py`, or the `thinking_config` in
`thinking.py`. The shared client, tracing, labeling, and output handling come from `_common.py`
unchanged.
