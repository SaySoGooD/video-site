from pydantic import BaseModel


class MessageResponse(BaseModel):
    """A deliberately uninformative acknowledgement.

    Used by the password-reset request, where the answer must be identical
    whether or not the address belongs to an account.
    """

    detail: str
