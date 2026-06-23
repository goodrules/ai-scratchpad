"""Run the same prompt across the latest Opus, Sonnet, and Haiku on Vertex AI."""

from __future__ import annotations

from _common import (
    HAIKU,
    OPUS,
    SONNET,
    default_metadata,
    get_client,
    print_header,
    print_response,
    tracer,
)

PROMPT = "In 2 sentences, explain why the sky is blue."
MODELS = [OPUS, SONNET, HAIKU]


def run() -> None:
    print_header(f"models :: {PROMPT!r}")
    client = get_client()
    # Same prompt, every model -- the only thing that varies is the `model` argument.
    for model in MODELS:
        with tracer.start_as_current_span("vertex-prediction"):
            response = client.messages.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "user", "content": PROMPT}],
                metadata=default_metadata(),
            )
        print_response(model, response)


if __name__ == "__main__":
    run()
