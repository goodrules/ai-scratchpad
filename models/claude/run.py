"""Meta runner: execute individual Claude-on-Vertex demos or the full set."""

from __future__ import annotations

import argparse

import models
import prompt_caching
import streaming
import structured_outputs
import thinking
import token_counting
import tools
import vision
import web_search

# Registry: demo name -> the run() entrypoint in that module. Each value is also runnable on its
# own via `uv run models/claude/<name>.py`.
DEMOS = {
    "models": models.run,
    "thinking": thinking.run,
    "streaming": streaming.run,
    "tools": tools.run,
    "structured_outputs": structured_outputs.run,
    "vision": vision.run,
    "web_search": web_search.run,
    "prompt_caching": prompt_caching.run,
    "token_counting": token_counting.run,
}

# Convenience alias. ("tools" is a demo name, so groups avoid reusing it.)
GROUPS = {
    "all": list(DEMOS),
}


def resolve(names: list[str]) -> list[str]:
    """Expand group names to demo names, validate, and dedupe while preserving order."""
    invalid = [n for n in names if n not in DEMOS and n not in GROUPS]
    if invalid:
        valid = sorted(set(DEMOS) | set(GROUPS))
        raise SystemExit(f"unknown demo or group: {invalid[0]!r}. valid: {valid}")
    return list(dict.fromkeys(d for name in names for d in GROUPS.get(name, [name])))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one or more Claude-on-Vertex demos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "demos:  " + ", ".join(sorted(DEMOS)) + "\n"
            "groups: " + ", ".join(sorted(GROUPS)) + "\n\n"
            "examples:\n"
            "  uv run models/claude/run.py all\n"
            "  uv run models/claude/run.py models thinking\n"
            "  uv run models/claude/run.py tools\n"
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
