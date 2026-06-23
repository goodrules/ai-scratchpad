"""Web search grounding via the server-side web_search tool (Vertex: basic web_search_20250305)."""

from __future__ import annotations

from _common import DEFAULT, default_metadata, get_client, print_header, print_response, tracer

PROMPT = "Who won the most recent Formula 1 Grand Prix, and where was it held?"

# Server-side tool: Anthropic runs the search and feeds results back in the same response. Vertex
# supports only the basic web_search_20250305 variant (no _20260209 dynamic filtering, no web_fetch).
TOOLS = [{"type": "web_search_20250305", "name": "web_search"}]


def run() -> None:
    print_header(f"web_search ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    messages = [{"role": "user", "content": PROMPT}]
    # The server-side tool loop can hit its iteration cap and return stop_reason="pause_turn";
    # re-send the assistant turn to let it resume (capped so a stuck loop can't run forever).
    response = None
    for _ in range(5):
        with tracer.start_as_current_span("vertex-prediction"):
            response = client.messages.create(
                model=DEFAULT,
                max_tokens=2048,
                tools=TOOLS,
                messages=messages,
                metadata=default_metadata(),
            )
        if response.stop_reason != "pause_turn":
            break
        messages = [
            {"role": "user", "content": PROMPT},
            {"role": "assistant", "content": response.content},
        ]
    print_response("answer", response)


if __name__ == "__main__":
    run()
