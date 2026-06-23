"""Count input tokens for a prompt with client.messages.count_tokens (model-specific; not tiktoken)."""

from __future__ import annotations

from _common import DEFAULT, console, get_client, print_header, tracer

PROMPT = "Summarize the plot of Moby-Dick in exactly three sentences."


def run() -> None:
    print_header(f"token_counting ({DEFAULT}) :: {PROMPT!r}")
    client = get_client()
    # count_tokens returns the exact, model-specific input token count without running inference --
    # use it for cost estimates and budget checks instead of an OpenAI-style tiktoken approximation.
    with tracer.start_as_current_span("vertex-prediction"):
        count = client.messages.count_tokens(
            model=DEFAULT,
            messages=[{"role": "user", "content": PROMPT}],
        )
    console.print()
    console.rule("[bold cyan]count_tokens[/bold cyan]", style="cyan", align="left")
    console.print(f"[bold]input_tokens[/bold] = {count.input_tokens}")


if __name__ == "__main__":
    run()
