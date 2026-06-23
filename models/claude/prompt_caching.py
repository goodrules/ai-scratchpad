"""Prompt caching: a large cached system prefix, billed once then read cheaply on the next call."""

from __future__ import annotations

from _common import DEFAULT, default_metadata, get_client, print_header, print_response, tracer

# A realistic support-policy "document" used as a large, stable system prefix. The two facts the
# questions below probe (the refund window and the enterprise-support contact) live up top; the rest
# is padding so the prefix comfortably clears Sonnet 4.6's ~2048-token minimum cacheable size.
_POLICY = """\
Acme Cloud — Customer Support Policy (v3).

Refunds: customers may request a full refund within 30 days of purchase. After 30 days, refunds are
prorated at the discretion of the billing team. Enterprise support contact: enterprise@acme.example.
Standard support is available via the in-product help widget during business hours (09:00–18:00 ET).

Severity definitions: S1 is a full production outage; S2 is degraded service with no workaround; S3
is a minor issue with a workaround; S4 is a question or feature request. Initial response targets are
30 minutes for S1, 2 hours for S2, one business day for S3, and two business days for S4.
"""
_FILLER = (
    "Acme Cloud commits to transparent communication, reproducible incident timelines, and a "
    "documented post-incident review for every S1 and S2 event, shared with affected customers. "
)
# Build appendices A–H of repeated guidance to push the prefix well past the cacheable minimum.
_DOC = _POLICY + "\n\n" + "\n\n".join(
    f"Appendix {chr(ord('A') + i)}. Operational guidance.\n" + _FILLER * 25 for i in range(8)
)

SYSTEM = [{"type": "text", "text": _DOC, "cache_control": {"type": "ephemeral"}}]

QUESTIONS = [
    "In one sentence, what is the document's stated refund window?",
    "In one sentence, what email should an enterprise customer contact for support?",
]


def run() -> None:
    print_header(f"prompt_caching ({DEFAULT}) :: {len(_DOC)} chars of cached system prefix")
    client = get_client()
    # Vertex does not support automatic caching, so mark the system block explicitly with
    # cache_control. Call 1 writes the cache (cache_write > 0); call 2 reuses the identical prefix
    # and reads it (cache_read > 0) -- only the per-call user question differs.
    for i, question in enumerate(QUESTIONS, start=1):
        with tracer.start_as_current_span("vertex-prediction"):
            response = client.messages.create(
                model=DEFAULT,
                max_tokens=256,
                system=SYSTEM,
                messages=[{"role": "user", "content": question}],
                metadata=default_metadata(),
            )
        print_response(f"call {i}", response)


if __name__ == "__main__":
    run()
