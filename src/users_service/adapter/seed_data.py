"""Demo data loaded on first start, so the API is usable straight away.

The permission set is deliberately tiny — this service only answers "who is
this user?", so the only resources it owns are accounts and the access-control
model itself. Anything about videos, comments or uploads belongs to the
services that own those objects, which check permissions issued from here.

Permissions (resource:action):
    account:read     — see any account, including soft-deleted ones
    account:moderate — deactivate / restore an account
    access_control:manage

Roles:
    admin     -> every permission (the seeded admin is also is_superuser)
    moderator -> account read + moderate
    user      -> no permissions; the default role every signup receives

Users (email / username / password):
    admin@example.com     / admin     / admin123      (superuser, role: admin)
    moderator@example.com / moderator / moderator123  (role: moderator)
    viewer@example.com    / viewer    / viewer123     (role: user)
"""

PERMISSIONS = [
    ("account", "read", "View any account, including soft-deleted ones"),
    ("account", "moderate", "Deactivate or restore an account"),
    ("access_control", "manage", "Manage roles and permissions"),
]

ROLE_GRANTS = {
    "admin": [(p[0], p[1]) for p in PERMISSIONS],
    "moderator": [
        ("account", "read"),
        ("account", "moderate"),
    ],
    "user": [],
}

ROLE_DESCRIPTIONS = {
    "admin": "Full access, including access-control management",
    "moderator": "Can review and deactivate accounts",
    "user": "Default role for a registered visitor",
}

# (email, username, password, display_name, is_superuser, role)
USERS = [
    ("admin@example.com", "admin", "admin123", "Alice", True, "admin"),
    (
        "moderator@example.com",
        "moderator",
        "moderator123",
        "Mod",
        False,
        "moderator",
    ),
    ("viewer@example.com", "viewer", "viewer123", "Vic", False, "user"),
]
