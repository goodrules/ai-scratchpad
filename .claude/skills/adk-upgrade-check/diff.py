#!/usr/bin/env python3
"""Compare two snapshots and print only what the upgrade changed.

Usage:
    uv run .claude/skills/adk-upgrade-check/diff.py before.json after.json

Exit status: 0 if nothing regressed, 1 if any agent broke, a warning appeared,
or lint got worse -- so this can gate CI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# An import that suddenly takes much longer usually means new module-scope
# network or subprocess work, which is worth surfacing even though it passes.
SLOWDOWN_FACTOR = 2.0
SLOWDOWN_FLOOR = 1.0  # seconds; ignore noise on fast imports


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    args = ap.parse_args()

    a, b = load(args.before), load(args.after)
    regressed = False
    out: list[str] = []

    out.append(f"ADK    {a['adk_version']}  ->  {b['adk_version']}")
    if a["python"] != b["python"]:
        out.append(f"Python {a['python']}  ->  {b['python']}")

    a_agents, b_agents = a["agents"], b["agents"]

    for gone in sorted(set(a_agents) - set(b_agents)):
        out.append(f"\n[removed] {gone} -- no longer discovered")
    for new in sorted(set(b_agents) - set(a_agents)):
        st = b_agents[new]["status"]
        out.append(f"\n[new] {new} -- {st}")
        if st != "ok":
            regressed = True

    for name in sorted(set(a_agents) & set(b_agents)):
        old, new = a_agents[name], b_agents[name]
        lines: list[str] = []

        if old["status"] != new["status"]:
            lines.append(f"  status: {old['status']} -> {new['status']}")
            if new["status"] != "ok":
                regressed = True
                if new.get("error"):
                    lines.append("  " + new["error"].replace("\n", "\n  "))
        elif new["status"] != "ok":
            lines.append(f"  still {new['status']} (pre-existing)")

        if old["root_agent_type"] != new["root_agent_type"]:
            lines.append(
                f"  root_agent type: {old['root_agent_type']} -> {new['root_agent_type']}"
            )
            regressed = True

        added = sorted(set(new["warnings"]) - set(old["warnings"]))
        cleared = sorted(set(old["warnings"]) - set(new["warnings"]))
        for w in added:
            lines.append(f"  + {w}")
            regressed = True
        for w in cleared:
            lines.append(f"  - {w}   (resolved)")

        ot, nt = old["import_seconds"], new["import_seconds"]
        if nt > SLOWDOWN_FLOOR and ot > 0 and nt / ot >= SLOWDOWN_FACTOR:
            lines.append(f"  import time: {ot}s -> {nt}s")

        if lines:
            out.append(f"\n{name}")
            out.extend(lines)

    a_ruff, b_ruff = a.get("ruff", {}), b.get("ruff", {})
    if a_ruff or b_ruff:
        ruff_lines: list[str] = []
        for name in sorted(set(a_ruff) | set(b_ruff)):
            if name == "_error":
                continue
            oc = a_ruff.get(name, {}).get("count", 0)
            nc = b_ruff.get(name, {}).get("count", 0)
            if oc == nc:
                continue
            codes = b_ruff.get(name, {}).get("codes", {})
            top = ", ".join(
                f"{c}x{n}" for c, n in sorted(codes.items(), key=lambda kv: -kv[1])[:4]
            )
            ruff_lines.append(f"  {name}: {oc} -> {nc}" + (f"   ({top})" if top else ""))
            if nc > oc:
                regressed = True
        if b_ruff.get("_error"):
            ruff_lines.append(f"  ruff did not run: {b_ruff['_error']}")
            regressed = True
        if ruff_lines:
            out.append("\nlint")
            out.extend(ruff_lines)

    print("\n".join(out))
    ok = sum(1 for x in b_agents.values() if x["status"] == "ok")
    print(f"\n{ok}/{len(b_agents)} agents import cleanly.")
    print("REGRESSIONS FOUND" if regressed else "No regressions.")
    return 1 if regressed else 0


if __name__ == "__main__":
    raise SystemExit(main())
