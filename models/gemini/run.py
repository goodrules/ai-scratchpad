"""Meta runner: execute individual Gemini demos or named groups."""

from __future__ import annotations

import argparse

import importlib

# Registry: demo name -> runner lambda. Lazily imported so --help and single runs are fast.
DEMOS = {
    "models": lambda: importlib.import_module("models").run(),
    "thinking": lambda: importlib.import_module("thinking").run(),
    "search": lambda: importlib.import_module("search").run(),
    "maps": lambda: importlib.import_module("maps").run(),
    "code_execution": lambda: importlib.import_module("code_execution").run(),
    "url_context": lambda: importlib.import_module("url_context").run(),
}

# Convenience aliases that expand to several demos.
GROUPS = {
    "tools": ["search", "maps", "code_execution", "url_context"],
    "all": ["models", "thinking", "search", "maps", "code_execution", "url_context"],
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
        description="Run one or more Gemini 3/3.5/3.7 demos.",
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
