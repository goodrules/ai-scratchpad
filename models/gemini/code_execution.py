"""gemini-3.7-flash + code execution. Surfaces executed code and its result."""

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

    parts = response.candidates[0].content.parts if response.candidates and response.candidates[0].content else []
    for part in parts:
        if part.executable_code:
            print_code_block(part.executable_code.code, _enum_name(part.executable_code.language))
        elif part.code_execution_result:
            print_execution_result(_enum_name(part.code_execution_result.outcome), part.code_execution_result.output)
        elif part.text:
            print_text("text", part.text)

    _render_usage(response.usage_metadata)


if __name__ == "__main__":
    run()
