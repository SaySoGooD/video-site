from datetime import datetime

from pydantic import BaseModel


class PublicUserResponse(BaseModel):
    """The account as **anyone else** sees it.

    A separate model rather than a filtered ``UserResponse``: a public profile
    can only ever leak a field that was deliberately put on it, so adding a
    private column to the user later cannot accidentally publish it.
    """

    id: int
    username: str
    display_name: str | None = None
    created_at: datetime | None = None
