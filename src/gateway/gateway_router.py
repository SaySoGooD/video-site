"""The single catch-all route that fronts every service.

One handler rather than a generated route per upstream endpoint: the gateway
should not have to be redeployed because a service added an endpoint. It knows
prefixes, not APIs.
"""

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from gateway.identity import IdentityResolver
from gateway.proxy import ProxyError, build_forward_headers, forward, unavailable
from gateway.routes import Route, match

router = APIRouter()

PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@router.api_route("/{path:path}", methods=PROXY_METHODS, include_in_schema=False)
async def proxy(request: Request, path: str) -> Response:
    """Resolve the caller if the route needs it, then forward the request."""
    config = request.app.state.config
    routes: list[Route] = request.app.state.routes
    client: httpx.AsyncClient = request.app.state.client
    resolver: IdentityResolver = request.app.state.identity_resolver

    route = match(routes, "/" + path)
    if route is None:
        return JSONResponse(status_code=404, content={"detail": "Unknown route"})

    if route.upstream is None:
        return unavailable(route.prefix.lstrip("/"))

    identity = None
    if route.inject_identity or route.require_identity:
        identity = await resolver.resolve(
            dict(request.headers), dict(request.cookies)
        )
        if identity is None and route.require_identity:
            return JSONResponse(
                status_code=401, content={"detail": "Authentication required"}
            )

    headers = build_forward_headers(
        request,
        identity,
        _client_ip(request, config),
        request.cookies.get(config.VISITOR_COOKIE_NAME),
    )
    target = f"{route.upstream.rstrip('/')}{config.API_PREFIX}/{path}"

    try:
        return await forward(client, request, target, headers)
    except ProxyError as exc:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": str(exc)}
        )


def _client_ip(request: Request, config: object) -> str | None:
    """The caller's address, as far as it can be trusted.

    ``X-Forwarded-For`` is only believed when the deployment says a proxy sits
    in front of the gateway; otherwise the peer address is the only honest
    answer.
    """
    if getattr(config, "TRUST_PROXY_HEADERS", False):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client is not None else None
