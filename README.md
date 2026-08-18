# ai-scratchpad

A small scratchpad for experimenting with frontier models on **Vertex AI** — runnable, read-and-copy
demos plus the observability wiring around them.

## Layout

- [`models/gemini/`](models/gemini/README.md) — runnable demos of Gemini 3/3.5/3.7 features (models, thinking, search, maps, code
  execution, URL context) plus shared client/observability setup in `_common.py`, and BigQuery
  token-usage SQL in `models/gemini/sql/`.
- [`models/claude/`](models/claude/README.md) — runnable demos of Anthropic Claude on Vertex AI (models, thinking, streaming,
  tool use, structured outputs, vision, web search, prompt caching, token counting) plus shared
  client/observability setup in `_common.py`.
- [`agents/`](agents/README.md) — autonomous agents, multi-agent workflows, and evaluation demos built on the **Google Agent Development Kit (ADK)** and **Vertex AI Agent Engine**.

Each model cookbook is self-contained with a `_common.py` hub, one tiny file per capability, and a `run.py`
meta-runner. See each subfolder's `README.md` for the deep dive.

## Setup

```bash
uv sync                                   # install dependencies
gcloud auth application-default login     # authenticate ADC (all cookbooks use ADC, no API keys)
```

Then copy and fill the `.env` for whichever cookbook or agent you're running:

```bash
cp models/gemini/.env.example models/gemini/.env     # Gemini
cp models/claude/.env.example models/claude/.env     # Claude
```

At minimum set `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION="global"` (recommended for dynamic routing and quota resilience).

## Run the demos

### 1. Model Capabilities

```bash
uv run models/gemini/run.py all           # every Gemini demo
uv run models/claude/run.py all           # every Claude demo
uv run models/claude/run.py models        # a single named demo
```

### 2. Autonomous Agents & Workflows (ADK)

```bash
# Run an ADK agent in the terminal
uv run adk run agents/adk/agents/google_search_agent/app
uv run adk run agents/adk/agents/short_story_agent

# Run local agent evaluation (Vertex AI EvalTask)
uv run python agents/demos/eval_sea_captain_local.py

# Launch the visual ADK web UI
cd agents/adk/agents && uv run adk web
```

See [`agents/README.md`](agents/README.md) for the full agent catalog, MCP tools, and deployment guides.

## Token usage (Gemini)

`models/gemini/sql/` holds BigQuery queries that report token usage from Vertex AI request/response
logging. Replace the `<PROJECT_ID>.<DATASET>.<LOGGING_TABLE>` placeholders (these map to
`GOOGLE_CLOUD_PROJECT` / `BIGQUERY_LOGGING_DESTINATION`), then run, e.g.:

```bash
bq query --use_legacy_sql=false --project_id=<PROJECT_ID> < models/gemini/sql/usage_by_caller.sql
```

> The label-based BigQuery attribution is Gemini-specific: the Anthropic Messages API has no Vertex
> `labels` field, so the Claude cookbook attributes usage via Anthropic's native `metadata.user_id`
> instead. See `models/claude/README.md` for details.

## References

Official documentation links for authentication, Google Gen AI SDK, Anthropic on Vertex AI, and ADK / Agent Engine are cataloged in [`REFERENCE.md`](REFERENCE.md).

