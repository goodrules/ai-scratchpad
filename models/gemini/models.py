"""Run the same prompt across all Gemini 3/3.5/3.7 models."""

from __future__ import annotations

from _common import (
    FLASH,
    FLASH_LITE,
    GEMMA,
    PRO,
    get_client,
    labeled_config,
    print_header,
    print_response,
    tracer,
)

PROMPT = "In 2 sentences, explain why the sky is blue."
MODELS = [PRO, FLASH, FLASH_LITE, GEMMA]


def run() -> None:
    print_header(f"models :: {PROMPT!r}")
    client = get_client()
    # Same prompt, every model -- the only thing that varies is the `model` argument.
    for model in MODELS:
        with tracer.start_as_current_span("vertex-prediction"):
            response = client.models.generate_content(
                model=model, contents=PROMPT, config=labeled_config()
            )
        print_response(model, response)


if __name__ == "__main__":
    run()
