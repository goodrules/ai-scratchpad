"""Stream a long response from claude-sonnet-4-6 token-by-token, then read final usage."""

from __future__ import annotations

from _common import DEFAULT, _render_usage, console, default_metadata, get_client, print_header, tracer

PROMPT = (
    "Write a vivid six-paragraph short story about a lighthouse keeper who finds "
    "a message in a bottle that seems to describe the next day's storm."
)


def run() -> None:
    print_header(f"streaming ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    console.print()
    console.rule("[bold cyan]story (streamed)[/bold cyan]", style="cyan", align="left")
    with tracer.start_as_current_span("vertex-prediction"):
        # messages.stream() accumulates state for you: iterate text_stream for live output, then
        # get_final_message() for the assembled message + usage. Streaming also avoids HTTP timeouts
        # on large max_tokens. (Use the builtin print for chunks so brackets aren't read as markup.)
        with client.messages.stream(
            model=DEFAULT,
            max_tokens=16000,
            messages=[{"role": "user", "content": PROMPT}],
            metadata=default_metadata(),
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            final = stream.get_final_message()
    print()
    _render_usage(getattr(final, "usage", None))


if __name__ == "__main__":
    run()
