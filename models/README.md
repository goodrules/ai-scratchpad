# models/

Read-and-copy cookbooks of frontier-model features on **Vertex AI**, one folder per provider. Each is
self-contained — a `_common.py` hub, one tiny file per capability, and a `run.py` meta-runner — and
authenticates with GCP ADC (`gcloud auth application-default login`); no provider API keys.

| Cookbook | Provider / SDK | Deep-dive |
| --- | --- | --- |
| [`gemini/`](gemini/README.md) | Google Gemini 3 via `google-genai` | Observability (Cloud Trace, BigQuery request/response logging, label-based per-caller attribution) + token-usage SQL in `gemini/sql/`. |
| [`claude/`](claude/README.md) | Anthropic Claude via `anthropic[vertex]` | Cloud Trace + console observability; per-caller attribution via the Anthropic-native `metadata.user_id` field (no BigQuery/labels — see that README for why). |

## Quick start

```bash
uv sync                                              # from the repo root
cp models/gemini/.env.example models/gemini/.env     # and/or models/claude/.env
gcloud auth application-default login

uv run models/gemini/run.py all
uv run models/claude/run.py all
```

See each subfolder's `README.md` for the full walkthrough, environment variables, and per-demo notes.
