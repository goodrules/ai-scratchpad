"""gemini-3.5-flash + URL Context."""

from __future__ import annotations

from _common import DEFAULT, get_client, labeled_config, print_header, print_response, tracer
from google.genai import types

URL = "https://ai.google.dev/gemini-api/docs/gemini-3"
PROMPT = f"In 5 bullet points, summarize the key features described at {URL}"


def run() -> None:
    print_header(f"url_context ({DEFAULT}) :: {URL}")
    client = get_client()
    with tracer.start_as_current_span("vertex-prediction"):
        response = client.models.generate_content(
            model=DEFAULT,
            contents=PROMPT,
            config=labeled_config(
                types.GenerateContentConfig(
                    # The URL Context tool lets the model fetch and read the URLs in the prompt.
                    tools=[types.Tool(url_context=types.UrlContext())],
                )
            ),
        )
    print_response("answer", response)


if __name__ == "__main__":
    run()
