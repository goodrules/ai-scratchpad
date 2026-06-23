"""Meta runner: execute individual Gemini demos or named groups."""

from __future__ import annotations

import argparse

import code_execution
import maps
import models
import search
import thinking
import url_context

# Registry: demo name -> the run() entrypoint in that module. Each value is also runnable on its
# own via `uv run models/gemini/<name>.py`.
DEMOS = {
    "models": models.run,
    "thinking": thinking.run,
    "search": search.run,
    "maps": maps.run,
    "code_execution": code_execution.run,
    "url_context": url_context.run,
}

# Convenience aliases that expand to several demos.
GROUPS = {
    "tools": ["search", "maps", "code_execution", "url_context"],
    "all": ["models", "thinking", "search", "maps", "code_execution", "url_context"],
}


def resolve(names: list[str]) -> list[str]:
    """Expand group names to demo names, validate, and dedupe while preserving order."""
    resolved: list[str] = []
    for name in names:
        if name in GROUPS:
            for demo in GROUPS[name]:
                if demo not in resolved:
                    resolved.append(demo)
        elif name in DEMOS:
            if name not in resolved:
                resolved.append(name)
        else:
            valid = sorted(set(DEMOS) | set(GROUPS))
            raise SystemExit(f"unknown demo or group: {name!r}. valid: {valid}")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one or more Gemini 3 demos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "demos:  " + ", ".join(sorted(DEMOS)) + "\n"
            "groups: " + ", ".join(sorted(GROUPS)) + "\n\n"
            "examples:\n"
            "  uv run models/gemini/run.py all\n"
            "  uv run models/gemini/run.py tools\n"
            "  uv run models/gemini/run.py search maps\n"
            "  uv run models/gemini/run.py thinking\n"
        ),
    )
    parser.add_argument(
        "demos",
        nargs="+",
        help="demo or group names to run",
    )
    args = parser.parse_args()

    for demo_name in resolve(args.demos):
        DEMOS[demo_name]()


if __name__ == "__main__":
    main()
