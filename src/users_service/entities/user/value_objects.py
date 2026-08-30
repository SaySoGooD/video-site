from typing import NewType

UserId = NewType("UserId", int)
Email = NewType("Email", str)
Username = NewType("Username", str)

# Opaque, non-guessable id of a *browser*, not of a person. Issued to every
# visitor (anonymous or not) and carried in a long-lived cookie, so analytics
# can join "what did this visitor do?" onto "who is this user?" without the
# analytics side ever seeing an email or a password.
VisitorId = NewType("VisitorId", str)
