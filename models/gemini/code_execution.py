"""gemini-3.5-flash + code execution. Surfaces executed code and its result."""

from __future__ import annotations

from _common import (
    DEFAULT,
    _enum_name,
    _render_usage,
    get_client,
    labeled_config,
    print_code_block,
    print_execution_result,
    print_header,
    print_text,
    tracer,
)
from google.genai import types

PROMPT = (
    "Using Python, compute the following with Bayes' theorem: a medical test "
    "for a rare disease has a 99% true-positive rate and a 99% true-negative "
    "rate. The disease affects 1 in 10,000 people. If a randomly selected "
    "person tests positive, what is the probability they actually have the "
    "disease? Show the code you ran and report the result as a percentage."
)


def run() -> None:
    print_header(f"code_execution ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    with tracer.start_as_current_span("vertex-prediction"):
        response = client.models.generate_content(
            model=DEFAULT,
            contents=PROMPT,
            config=labeled_config(
                types.GenerateContentConfig(
                    tools=[types.Tool(code_execution=types.ToolCodeExecution())],
                )
            ),
        )

    # A code-execution response is a sequence of typed parts -- typically the model's generated
    # `executable_code`, then the platform's `code_execution_result`, then a `text` summary. We
    # walk them by type (rather than using print_response()) so we can render code and output
    # distinctly. `language`/`outcome` are protobuf enums; _enum_name normalizes them to strings.
    candidates = getattr(response, "candidates", None) or []
    parts = []
    if candidates and candidates[0].content:
        parts = candidates[0].content.parts or []

    for part in parts:
        if getattr(part, "executable_code", None):
            code = part.executable_code
            language = _enum_name(getattr(code, "language", "PYTHON"))
            print_code_block(getattr(code, "code", ""), language)
        elif getattr(part, "code_execution_result", None):
            result = part.code_execution_result
            outcome = _enum_name(getattr(result, "outcome", ""))
            print_execution_result(outcome, getattr(result, "output", ""))
        elif getattr(part, "text", None):
            print_text("text", part.text)

    _render_usage(getattr(response, "usage_metadata", None))


if __name__ == "__main__":
    run()
