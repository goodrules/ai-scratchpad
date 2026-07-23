"""gemini-3.6-flash + Google Maps grounding (lat/lng resolved via structured output)."""

from __future__ import annotations

from pydantic import BaseModel

from _common import DEFAULT, get_client, labeled_config, print_header, print_response, tracer
from google.genai import types

LOCATION = "Roswell, GA"
PROMPT = "What are some highly rated coffee shops within a 10 minute walk?"


class Coordinates(BaseModel):
    latitude: float
    longitude: float


def resolve_coordinates(client, location: str) -> Coordinates:
    print_header(f"resolve_coordinates ({DEFAULT}) :: {location!r}")
    with tracer.start_as_current_span("vertex-prediction"):
        response = client.models.generate_content(
            model=DEFAULT,
            contents=f"What are the latitude and longitude of {location}?",
            config=labeled_config(
                types.GenerateContentConfig(
                    # Structured output: ask for JSON matching the Coordinates schema, then read
                    # the deserialized object off response.parsed.
                    response_mime_type="application/json",
                    response_schema=Coordinates,
                )
            ),
        )
    return response.parsed


def run() -> None:
    client = get_client()
    # Two calls: Maps grounding needs a lat/lng anchor, so we first resolve coordinates for the
    # location (via structured output above), then ground the actual question on that point.
    coords = resolve_coordinates(client, LOCATION)

    print_header(
        f"google_maps ({DEFAULT}) @ ({coords.latitude}, {coords.longitude}) "
        f":: {PROMPT!r}"
    )
    # Anchor the Maps tool at the resolved coordinates via tool_config.retrieval_config.
    lat_lng = types.LatLng(latitude=coords.latitude, longitude=coords.longitude)
    tool_config = types.ToolConfig(
        retrieval_config=types.RetrievalConfig(lat_lng=lat_lng)
    )
    with tracer.start_as_current_span("vertex-prediction"):
        response = client.models.generate_content(
            model=DEFAULT,
            contents=PROMPT,
            config=labeled_config(
                types.GenerateContentConfig(
                    tools=[types.Tool(google_maps=types.GoogleMaps())],
                    tool_config=tool_config,
                )
            ),
        )
    print_response("answer", response)


if __name__ == "__main__":
    run()
