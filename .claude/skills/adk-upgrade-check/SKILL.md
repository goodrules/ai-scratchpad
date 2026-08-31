---
name: adk-upgrade-check
version: 1.0.0
description: |
  Verify every ADK agent under agents/adk/agents still works after a google-adk
  version bump. Takes a before/after snapshot of imports, deprecation warnings,
  import timing and lint, then reports only the deltas. Use when: "bump adk",
  "upgrade google-adk", "did the adk update break anything", "check the agents
  after the sdk upgrade", or before merging any change to the google-adk pin.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Grep
  - Glob
---

# ADK upgrade check

Importing an ADK agent exercises its entire wiring, because agents build their
tool and sub-agent graph at module scope. That makes a plain import a
surprisingly strong smoke test — and it needs no network or credentials.

The point of this skill is the **diff**, not the snapshot. A bare "6/6 import"
tells you nothing about what the upgrade silently changed; comparing two runs
tells you exactly which warnings are new, which agent broke, and where.

## Procedure

**1. Baseline on the current pin, before touching anything.**

```bash
uv run .claude/skills/adk-upgrade-check/snapshot.py -o /tmp/adk_before.json
```

If any agent is already failing, note it — the diff labels it `pre-existing` so
you don't misattribute it to the upgrade.

**2. Bump the pin and sync.**

The version lives in the root `pyproject.toml` as `google-adk[a2a,mcp]`. Keep
the extras. Then update the per-agent pyprojects that name `google-adk` so they
don't contradict what's installed:

```bash
rg -n 'google-adk' --glob '**/pyproject.toml'
uv sync
```

**3. Snapshot again and diff.**

```bash
uv run .claude/skills/adk-upgrade-check/snapshot.py -o /tmp/adk_after.json
uv run .claude/skills/adk-upgrade-check/diff.py /tmp/adk_before.json /tmp/adk_after.json
```

Exits 1 on any regression, so it can gate CI.

**4. Triage each delta.** See the table below, then re-run step 3 until clean.

**5. Confirm with the committed test.**

```bash
uv run --with pytest pytest tests/integration/test_adk_agents_import.py -q
```

If `snapshot.py` discovered an agent that test doesn't cover, add it — discovery
is automatic here but hardcoded there.

## Reading the diff

| Signal | What it usually means |
|---|---|
| `ImportError: cannot import name X` | **Check for a missing optional extra before assuming a rename.** ADK wraps optional imports in `try/except ImportError` and sets `__all__ = []`, so an uninstalled extra (`mcp`, `a2a`, `eval`, `toolbox`) looks exactly like a removed symbol. Confirm with `uv run python -c "import mcp"` before editing any import. |
| `ModuleNotFoundError` on a `google.adk.*` path | Genuine move. ADK 2.x relocated integrations, e.g. `tools.langchain_tool` → `integrations.langchain`. |
| New `DeprecationWarning` from `<repo>` | Yours to fix now, while the alias still works. |
| New `DeprecationWarning` from `<site>` | Inside ADK or a transitive dep. Record it, don't chase it. |
| `root_agent type` changed | A base class changed underneath you (e.g. `LlmAgent` → `Workflow`). Always investigate; nothing benign does this. |
| `import time` grew | Module-scope network or subprocess work. Anything over ~2s is doing real I/O at import. |
| lint count grew | Usually a `UP`/`B` rule reacting to newly-reachable code, occasionally a real bug. |

## Blind spots — check these by hand

The automation cannot see past a swallowed exception, and several agents
initialize tools inside bare `except Exception` blocks that null the tool out.
**An agent can import perfectly while half its tools are silently missing.**
After any upgrade, grep for the pattern and verify each fallback still takes the
success path:

```bash
rg -n -B3 'except Exception' agents/adk/agents --glob '!**/.venv/**'
```

Also not covered, because none of it runs at import time:

- **Runtime behaviour.** Nothing here calls a model. Prompt regressions, tool
  schema changes and state-key wiring all pass this check.
- **Servers and deployment.** `__main__.py` entrypoints and `deployment/`
  scripts aren't imported. If the a2a or Agent Engine surface moved, this is
  silent — check those files directly.
- **Instruction templating.** ADK does *not* unescape `{{` in instructions, so
  doubled braces reach the model literally. Verify with a real
  `inject_session_state` call rather than reasoning about it.

## Notes

- `snapshot.py` discovers agents by finding `agent.py` at depth 2 or 3 under
  `agents/adk/agents`, skipping `sub_agents/`. New agents are picked up with no
  edit; a new *layout* needs one.
- Each import runs in its own subprocess, so a crash or a module-name collision
  between agents can't take down the run.
- Warnings are normalized (paths, versions and addresses stripped) so the diff
  stays stable across machines and doesn't churn on patch bumps.
- Stale nested `.venv` directories shadow the root env and produce confusing
  failures. If one agent fails in a way that makes no sense, check for one.
