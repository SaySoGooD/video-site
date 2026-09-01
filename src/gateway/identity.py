"""Working out who is calling, and telling the services downstream.

The gateway does not verify tokens itself. It asks users-service — the service
that owns sessions — on every request that needs an identity. That costs one
extra hop, and buys the thing a locally verified JWT cannot give: a revoked
session stops working *immediately* rather than when its access token happens
to expire. For a site where "sign out my other devices" and "ban this account"
are supposed to mean something right now, that is the trade worth making.

What travels downstream is a set of ``X-User-*`` headers. Those headers are
therefore a credential in their own right: a service behind the gateway
believes them. The gateway strips any that arrived from the client
(:func:`strip_client_identity`) before it ever adds its own — without that,
anyone could simply send ``X-User-Id: 1`` and be an administrator.
"""

from dataclasses import dataclass, field
from typing import Any

import httpx

# Everything the gateway asserts about the caller. Nothing else may cross the
# boundary under one of these names.
IDENTITY_HEADERS = (
    "x-user-id",
    "x-user-username",
    "x-user-permissions",
    "x-user-superuser",
    "x-user-email-verified",
    "x-visitor-id",
)


@dataclass
class Identity:
    """The caller, as far as users-service is concerned."""

    user_id: int
    username: str
    permissions: list[str] = field(default_factory=list)
    is_superuser: bool = False
    email_verified: bool = False
    #: The browser the *account* was created from. Kept for completeness; the
    #: visitor id sent downstream is the one on the current request, which is
    #: not the same thing once a person uses a second device.
    visitor_id: str | None = None

    @classmethod
    def from_profile(cls, profile: dict[str, Any]) -> "Identity":
        return cls(
            user_id=int(profile["id"]),
            username=str(profile["username"]),
            permissions=list(profile.get("permissions") or []),
            is_superuser=bool(profile.get("is_superuser")),
            email_verified=bool(profile.get("email_verified")),
            visitor_id=profile.get("visitor_id"),
        )

    def as_headers(self) -> dict[str, str]:
        return {
            "X-User-Id": str(self.user_id),
            "X-User-Username": self.username,
            "X-User-Permissions": ",".join(self.permissions),
            "X-User-Superuser": "true" if self.is_superuser else "false",
            "X-User-Email-Verified": "true" if self.email_verified else "false",
        }


def strip_client_identity(headers: dict[str, str]) -> dict[str, str]:
    """Drop identity headers that came from the client.

    The gateway is the only thing allowed to speak in this vocabulary.
    """
    return {
        name: value
        for name, value in headers.items()
        if name.lower() not in IDENTITY_HEADERS
    }


class IdentityResolver:
    """Asks users-service who the caller is, forwarding their credentials."""

    def __init__(self, client: httpx.AsyncClient, users_service_url: str, api_prefix: str) -> None:
        self._client = client
        self._url = users_service_url.rstrip("/") + api_prefix + "/auth/me"

    async def resolve(self, headers: dict[str, str], cookies: dict[str, str]) -> Identity | None:
        """Return the caller, or ``None`` if the request is anonymous.

        Only the credential headers are forwarded — the rest of the incoming
        request has no business influencing an identity lookup. An upstream
        that is down or slow yields ``None`` (anonymous) rather than an error:
        this call is also made for routes that merely *prefer* an identity, and
        a service that requires one will refuse on its own.
        """
        forwarded = {
            name: value
            for name, value in headers.items()
            if name.lower() in ("authorization", "cookie")
        }

        try:
            response = await self._client.get(
                self._url, headers=forwarded, cookies=cookies
            )
        except httpx.HTTPError:
            return None

        if response.status_code != 200:
            return None

        return Identity.from_profile(response.json())
