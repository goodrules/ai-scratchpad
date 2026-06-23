"""Run claude-sonnet-4-6 with adaptive thinking at three effort levels (low/medium/high)."""

from __future__ import annotations

from _common import DEFAULT, default_metadata, get_client, print_header, print_response, tracer

PROMPT = (
    "A medical test for a rare disease has a 99% true-positive rate and a 99% "
    "true-negative rate. The disease affects 1 in 10,000 people in the general "
    "population. A randomly selected person tests positive. What is the "
    "probability that they actually have the disease? Walk through your "
    "reasoning step by step, state any assumptions, and show the calculation."
)
EFFORTS = ["low", "medium", "high"]


def run() -> None:
    print_header(f"thinking ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    for effort in EFFORTS:
        with tracer.start_as_current_span("vertex-prediction"):
            response = client.messages.create(
                model=DEFAULT,
                max_tokens=12000,
                # Adaptive thinking lets Claude decide how much to think; `effort` tunes the depth
                # and overall token spend. display="summarized" returns a readable thinking summary
                # (the default is "omitted", which leaves thinking blocks empty).
                thinking={"type": "adaptive", "display": "summarized"},
                output_config={"effort": effort},
                messages=[{"role": "user", "content": PROMPT}],
                metadata=default_metadata(),
            )
        print_response(f"effort={effort}", response)


if __name__ == "__main__":
    run()
