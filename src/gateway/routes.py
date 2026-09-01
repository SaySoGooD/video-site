"""The routing table: which prefix belongs to which service.

Deliberately a plain data structure rather than a config-file DSL. There are a
handful of services, the mapping changes when one is added, and a table you can
read in ten seconds is worth more than one you can edit without redeploying.
"""

from dataclasses import dataclass

from gateway.config import GatewayConfig


@dataclass(frozen=True)
class Route:
    """One prefix of the public API and the service that answers it."""

    prefix: str
    upstream: str | None
    #: Ask users-service who the caller is and pass the answer downstream.
    #: Off for users-service itself, which authenticates the request anyway —
    #: asking it who the caller is before forwarding to it would double every
    #: call for nothing.
    inject_identity: bool
    #: Refuse anonymous callers at the gateway instead of forwarding them.
    require_identity: bool = False


def build_routes(config: GatewayConfig) -> list[Route]:
    """Longest prefix first, so ``/users/me`` cannot be shadowed by ``/users``."""
    routes = [
        Route(prefix="/auth", upstream=config.USERS_SERVICE_URL, inject_identity=False),
        Route(prefix="/users", upstream=config.USERS_SERVICE_URL, inject_identity=False),
        Route(prefix="/admin", upstream=config.USERS_SERVICE_URL, inject_identity=False),
        # Not built yet: an unset URL makes this route answer 503 rather than
        # 404, which is the honest difference between "no such API" and "that
        # part of the system is not running".
        Route(
            prefix="/content",
            upstream=config.CONTENT_SERVICE_URL,
            inject_identity=True,
        ),
    ]
    return sorted(routes, key=lambda route: len(route.prefix), reverse=True)


def match(routes: list[Route], path: str) -> Route | None:
    """Return the route owning ``path`` (already stripped of the API prefix)."""
    for route in routes:
        if path == route.prefix or path.startswith(route.prefix + "/"):
            return route
    return None
