#!/usr/bin/env python3
"""Capture the health of every ADK agent as a diffable JSON snapshot.

Run once before an SDK bump and once after; `diff.py` reports only what moved.
Each agent is imported in its own subprocess so that one hard failure (or a
sys.path / module-name collision between agents) cannot take down the run.

Usage:
    uv run .claude/skills/adk-upgrade-check/snapshot.py -o before.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO / "agents" / "adk" / "agents"

# Importing an agent runs its whole module-scope wiring (tools, sub-agents,
# and any I/O it should not be doing). Anything slower than this is hung.
IMPORT_TIMEOUT = 120

# Child prints one JSON line on stdout. Warnings are forced to `always` so a
# deprecation that ADK only emits once still shows up on every run.
CHILD = r"""
import json, sys, time, warnings, traceback
warnings.simplefilter("always")
sys.path.insert(0, sys.argv[1])
caught = []
with warnings.catch_warnings(record=True) as log:
    warnings.simplefilter("always")
    t0 = time.perf_counter()
    try:
        import importlib
        mod = importlib.import_module(sys.argv[2])
        root = getattr(mod, "root_agent", None)
        out = {
            "status": "ok" if root is not None else "no_root_agent",
            "root_agent_type": type(root).__name__ if root is not None else None,
        }
    except BaseException:
        out = {"status": "fail", "root_agent_type": None,
               "error": traceback.format_exc(limit=6).strip()}
    elapsed = time.perf_counter() - t0
    caught = [
        {"category": w.category.__name__, "message": str(w.message),
         "filename": w.filename, "lineno": w.lineno}
        for w in log
    ]
out["import_seconds"] = round(elapsed, 2)
out["warnings"] = caught
print("@@SNAPSHOT@@" + json.dumps(out))
"""


def discover() -> list[tuple[str, Path, str]]:
    """Find root agents: (id, dir to put on sys.path, module to import).

    Two layouts exist in this repo -- a package sitting directly in the agents
    dir (`doc_understanding/agent.py`) and a project dir wrapping its package
    (`travel-concierge/travel_concierge/agent.py`). Nested `sub_agents/` are
    not roots; they get imported transitively by their parent.
    """
    found = []
    for path in sorted(AGENTS_DIR.rglob("agent.py")):
        rel = path.relative_to(AGENTS_DIR).parts
        if "sub_agents" in rel or ".venv" in rel or "node_modules" in rel:
            continue
        if len(rel) == 2:  # <pkg>/agent.py
            found.append((rel[0], AGENTS_DIR, f"{rel[0]}.agent"))
        elif len(rel) == 3:  # <project>/<pkg>/agent.py
            found.append((rel[0], AGENTS_DIR / rel[0], f"{rel[1]}.agent"))
    return found


def normalize(w: dict) -> str:
    """Collapse a warning to a stable identity so snapshots diff cleanly.

    Absolute paths, memory addresses and version numbers all churn between
    runs without meaning anything; the category, the message shape and the
    source location are what we actually want to compare.
    """
    msg = re.sub(r"0x[0-9a-f]+", "0xADDR", str(w["message"]))
    msg = re.sub(r"\d+\.\d+(\.\d+)?", "N.N", msg)
    msg = " ".join(msg.split())[:200]
    fn = w["filename"] or "?"
    for root, label in ((str(REPO), "<repo>"), (sys.prefix, "<site>")):
        if fn.startswith(root):
            fn = label + fn[len(root):]
            break
    return f"{w['category']}: {msg}  @ {fn}:{w['lineno']}"


def import_agent(agent_id: str, path_entry: Path, module: str) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", CHILD, str(path_entry), module],
            capture_output=True, text=True, timeout=IMPORT_TIMEOUT, cwd=path_entry,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "root_agent_type": None,
                "error": f"import exceeded {IMPORT_TIMEOUT}s -- blocking I/O at module scope?",
                "import_seconds": float(IMPORT_TIMEOUT), "warnings": []}

    marker = [ln for ln in proc.stdout.splitlines() if ln.startswith("@@SNAPSHOT@@")]
    if not marker:
        # Child died before it could report -- a segfault, or an import that
        # called sys.exit()/os._exit() at module scope.
        return {"status": "crash", "root_agent_type": None,
                "error": (proc.stderr or proc.stdout or "no output").strip()[-1200:],
                "import_seconds": round(time.perf_counter() - started, 2), "warnings": []}

    res = json.loads(marker[0][len("@@SNAPSHOT@@"):])
    res["warnings"] = sorted({normalize(w) for w in res["warnings"]})
    return res


def run_ruff() -> dict:
    """Lint the agents tree in one pass, grouped by agent.

    A single invocation is enough: ruff resolves per-file config itself, so
    each agent's pyproject (and its `extend` back to the root) still applies.
    """
    try:
        proc = subprocess.run(
            ["uvx", "ruff", "check", "--output-format", "json", "--no-cache", str(AGENTS_DIR)],
            capture_output=True, text=True, timeout=300, cwd=REPO,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"_error": f"ruff unavailable: {type(exc).__name__}"}

    if not proc.stdout.strip():
        return {"_error": (proc.stderr or "ruff produced no output").strip()[-600:]}
    try:
        issues = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"_error": (proc.stderr or proc.stdout).strip()[-600:]}

    by_agent: dict[str, dict] = {}
    for issue in issues:
        try:
            rel = Path(issue["filename"]).resolve().relative_to(AGENTS_DIR)
        except ValueError:
            continue
        bucket = by_agent.setdefault(rel.parts[0], {"count": 0, "codes": {}})
        bucket["count"] += 1
        code = issue.get("code") or "?"
        bucket["codes"][code] = bucket["codes"].get(code, 0) + 1
    return by_agent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", type=Path, required=True, help="snapshot JSON path")
    ap.add_argument("--no-ruff", action="store_true", help="skip the lint pass")
    args = ap.parse_args()

    try:
        import google.adk as adk
        adk_version = getattr(adk, "__version__", "unknown")
    except Exception as exc:
        adk_version = f"import failed: {exc}"

    snap = {
        "adk_version": adk_version,
        "python": sys.version.split()[0],
        "agents": {},
    }

    agents = discover()
    if not agents:
        print(f"error: no agents found under {AGENTS_DIR}", file=sys.stderr)
        return 2

    for agent_id, path_entry, module in agents:
        print(f"  importing {agent_id} ...", end="", flush=True, file=sys.stderr)
        res = import_agent(agent_id, path_entry, module)
        snap["agents"][agent_id] = res
        print(f" {res['status']} ({res['import_seconds']}s, "
              f"{len(res['warnings'])} warnings)", file=sys.stderr)

    if not args.no_ruff:
        print("  running ruff ...", end="", flush=True, file=sys.stderr)
        snap["ruff"] = run_ruff()
        total = sum(v["count"] for v in snap["ruff"].values() if isinstance(v, dict) and "count" in v)
        print(f" {total} issues", file=sys.stderr)

    args.out.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n")
    ok = sum(1 for a in snap["agents"].values() if a["status"] == "ok")
    print(f"\nwrote {args.out}  ({ok}/{len(snap['agents'])} agents ok)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
