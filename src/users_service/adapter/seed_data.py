"""Demo data loaded on first start, so the API is usable straight away.

The permission set stays small on purpose. This service answers "who is this
user?", so it defines the vocabulary of rights and hands them out; the services
that own videos, comments and uploads are the ones that check them. Adding a
permission here costs nothing later — inventing a taxonomy up front does.

Permissions (resource.action):
    content.read      — watch published content
    content.moderate  — take content down, review reports
    users.read        — see any account, including soft-deleted ones
    users.ban         — deactivate or restore an account
    users.manage      — administer roles and permissions

Roles:
    admin      -> every permission (the seeded admin is also is_superuser)
    moderator  -> content read/moderate, users read/ban
    user       -> content.read; the default role every signup receives

Users (email / username / password):
    admin@example.com     / admin     / admin123      (superuser, role: admin)
    moderator@example.com / moderator / moderator123  (role: moderator)
    viewer@example.com    / viewer    / viewer123     (role: user)
"""

PERMISSIONS = [
    ("content", "read", "Watch published content"),
    ("content", "moderate", "Take content down and review reports"),
    ("users", "read", "View any account, including soft-deleted ones"),
    ("users", "ban", "Deactivate or restore an account"),
    ("users", "manage", "Administer roles and permissions"),
]

ROLE_GRANTS = {
    "admin": [(p[0], p[1]) for p in PERMISSIONS],
    "moderator": [
        ("content", "read"),
        ("content", "moderate"),
        ("users", "read"),
        ("users", "ban"),
    ],
    "user": [
        ("content", "read"),
    ],
}

ROLE_DESCRIPTIONS = {
    "admin": "Full access, including role and permission administration",
    "moderator": "Reviews content and accounts",
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
