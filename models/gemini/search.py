"""gemini-3.6-flash + Google Search grounding."""

from __future__ import annotations

from _common import DEFAULT, get_client, labeled_config, print_header, print_response, tracer
from google.genai import types

PROMPT = "Who won the most recent Formula 1 Grand Prix, and where was it held?"


def run() -> None:
    print_header(f"google_search ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    with tracer.start_as_current_span("vertex-prediction"):
        response = client.models.generate_content(
            model=DEFAULT,
            contents=PROMPT,
            config=labeled_config(
                types.GenerateContentConfig(
                    # The Google Search tool lets the model ground its answer in live web results.
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                )
            ),
        )
    print_response("answer", response)


if __name__ == "__main__":
    run()
