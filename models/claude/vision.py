"""Vision: describe an image. Fetches a sample image at runtime and sends it as base64."""

from __future__ import annotations

import base64

import httpx

from _common import DEFAULT, default_metadata, get_client, print_header, print_response, tracer

# Any public image works -- swap this for your own. We fetch + base64-encode it because base64 is
# the most portable image source on Vertex; a {"type": "url"} source is the alternative.
IMAGE_URL = "https://picsum.photos/id/26/400/600"
PROMPT = "Describe this image in 3 short bullet points. What is the main subject and mood?"


def run() -> None:
    print_header(f"vision ({DEFAULT}) :: {IMAGE_URL}")
    client = get_client()

    resp = httpx.get(IMAGE_URL, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    # Vertex accepts image/jpeg, image/png, image/gif, image/webp -- read it from the response.
    media_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    data = base64.standard_b64encode(resp.content).decode("utf-8")

    with tracer.start_as_current_span("vertex-prediction"):
        response = client.messages.create(
            model=DEFAULT,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": data},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }],
            metadata=default_metadata(),
        )
    print_response("description", response)


if __name__ == "__main__":
    run()
