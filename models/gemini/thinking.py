"""Run gemini-3.6-flash at all four thinking tiers (minimal/low/medium/high)."""

from __future__ import annotations

from _common import DEFAULT, get_client, labeled_config, print_header, print_response, tracer
from google.genai import types

PROMPT = (
    "A medical test for a rare disease has a 99% true-positive rate and a 99% "
    "true-negative rate. The disease affects 1 in 10,000 people in the general "
    "population. A randomly selected person tests positive. What is the "
    "probability that they actually have the disease? Walk through your "
    "reasoning step by step, state any assumptions, and show the calculation."
)
TIERS = ["minimal", "low", "medium", "high"]


def run() -> None:
    print_header(f"thinking ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    for tier in TIERS:
        with tracer.start_as_current_span("vertex-prediction"):
            response = client.models.generate_content(
                model=DEFAULT,
                contents=PROMPT,
                config=labeled_config(
                    types.GenerateContentConfig(
                        # thinking_level controls reasoning depth; compare tiers on one prompt.
                        thinking_config=types.ThinkingConfig(thinking_level=tier),
                    )
                ),
            )
        print_response(f"thinking_level={tier}", response)


if __name__ == "__main__":
    run()
