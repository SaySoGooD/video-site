from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitPolicy:
    """How many attempts a key gets, and over what window.

    Bundled into one value so a use case takes "the policy for logins per IP"
    rather than two loose integers that are easy to swap by accident.
    """

    limit: int
    window_seconds: int

    @property
    def is_enforced(self) -> bool:
        """A non-positive limit disables the rule outright."""
        return self.limit > 0
