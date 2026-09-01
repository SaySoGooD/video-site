"""Forwarding a request to a service and streaming the answer back.

Streaming in both directions matters more than it looks: a video upload must
not be buffered whole in the gateway's memory, and neither must a download.
``httpx`` streams the response, and the request body is handed over as the
async iterator Starlette already gives us.
"""

import uuid
from collections.abc import AsyncIterator

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from gateway.identity import Identity, strip_client_identity

# Hop-by-hop headers belong to a single connection and must not be forwarded
# (RFC 9110). Passing on ``Connection`` or a stale ``Content-Length`` is how a
# proxy corrupts a response.
HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "host",
    }
)

REQUEST_ID_HEADER = "X-Request-Id"


class ProxyError(Exception):
    """An upstream could not be reached or did not answer in time."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(detail)


def unavailable(service: str) -> JSONResponse:
    """The answer for a route whose service is not deployed yet."""
    return JSONResponse(
        status_code=503,
        content={"detail": f"{service} is not available"},
    )


def build_forward_headers(
    request: Request,
    identity: Identity | None,
    client_ip: str | None,
    visitor_id: str | None = None,
) -> dict[str, str]:
    """Assemble the headers the upstream will see.

    Order matters: the client's own identity headers are stripped *first*, and
    only then are the gateway's own added. A service downstream trusts these,
    so a client must never be able to smuggle one through.
    """
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in HOP_BY_HOP
    }
    headers = strip_client_identity(headers)

    if identity is not None:
        headers.update(identity.as_headers())

    if visitor_id:
        headers["X-Visitor-Id"] = visitor_id

    if client_ip:
        forwarded = request.headers.get("x-forwarded-for")
        headers["X-Forwarded-For"] = (
            f"{forwarded}, {client_ip}" if forwarded else client_ip
        )
    headers["X-Forwarded-Proto"] = request.url.scheme
    headers.setdefault(
        REQUEST_ID_HEADER,
        request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex,
    )
    return headers


async def forward(
    client: httpx.AsyncClient,
    request: Request,
    target_url: str,
    headers: dict[str, str],
) -> StreamingResponse:
    """Send the request upstream and stream the response straight back."""
    upstream_request = client.build_request(
        method=request.method,
        url=target_url,
        headers=headers,
        params=request.query_params,
        content=_body_stream(request),
    )

    try:
        upstream_response = await client.send(upstream_request, stream=True)
    except httpx.TimeoutException as exc:
        raise ProxyError(504, "The upstream service timed out") from exc
    except httpx.HTTPError as exc:
        raise ProxyError(502, "The upstream service is unreachable") from exc

    # Rebuilt from the raw header list, not a dict: a login response carries
    # several Set-Cookie headers, and collapsing them into a mapping would
    # silently drop all but one.
    forwarded_headers = [
        (name, value)
        for name, value in upstream_response.headers.raw
        if name.decode("latin-1").lower() not in HOP_BY_HOP
    ]

    response = StreamingResponse(
        upstream_response.aiter_raw(),
        status_code=upstream_response.status_code,
        # Closing the upstream response is what returns its connection to the
        # pool; without this the gateway leaks one per proxied request.
        background=BackgroundTask(upstream_response.aclose),
    )
    response.raw_headers = forwarded_headers
    return response


async def _body_stream(request: Request) -> AsyncIterator[bytes]:
    async for chunk in request.stream():
        yield chunk
