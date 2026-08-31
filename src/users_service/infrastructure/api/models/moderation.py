from pydantic import BaseModel, Field


class BanUserRequest(BaseModel):
    """Why an account is being banned.

    The reason is optional but goes straight into the audit row, which is the
    only place the story of a ban is kept — worth filling in.
    """

    reason: str | None = Field(default=None, max_length=500)
