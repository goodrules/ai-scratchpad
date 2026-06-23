"""Structured output: extract typed fields from free text via client.messages.parse()."""

from __future__ import annotations

from pydantic import BaseModel

from _common import DEFAULT, _render_usage, console, default_metadata, get_client, print_header, tracer

TEXT = (
    "Hi, this is Priya Raman. I'd like to upgrade our team to the Enterprise plan. "
    "We're a team of 45, mainly interested in the API and SSO, and we'd love a demo "
    "next week. You can reach me at priya@acme.example."
)


class Lead(BaseModel):
    name: str
    email: str
    plan: str
    team_size: int
    interests: list[str]
    demo_requested: bool


def run() -> None:
    print_header(f"structured_outputs ({DEFAULT}) :: extract a sales lead")
    client = get_client()
    # messages.parse() constrains the response to the Pydantic schema and returns a validated
    # instance on response.parsed_output -- no manual JSON parsing or retry loop.
    with tracer.start_as_current_span("vertex-prediction"):
        response = client.messages.parse(
            model=DEFAULT,
            max_tokens=1024,
            messages=[{"role": "user", "content": f"Extract the lead details:\n\n{TEXT}"}],
            output_format=Lead,
            metadata=default_metadata(),
        )
    lead = response.parsed_output
    console.print()
    console.rule("[bold cyan]parsed Lead[/bold cyan]", style="cyan", align="left")
    console.print(lead.model_dump())
    _render_usage(getattr(response, "usage", None))


if __name__ == "__main__":
    run()
