"""Backend-neutral demo data, shared by the SQLAlchemy and in-memory seeders.

Permissions (resource:action):
    document:read/create/update/delete, report:read/export,
    access_control:manage

Roles:
    admin   -> every permission (also flagged is_superuser on the user)
    editor  -> document read/create/update, report read
    viewer  -> document read, report read

Users (email / password):
    admin@example.com  / admin123   (superuser, role: admin)
    editor@example.com / editor123  (role: editor)
    viewer@example.com / viewer123  (role: viewer)
"""

PERMISSIONS = [
    ("document", "read", "View documents"),
    ("document", "create", "Create documents"),
    ("document", "update", "Edit documents"),
    ("document", "delete", "Delete documents"),
    ("report", "read", "View reports"),
    ("report", "export", "Export reports"),
    ("access_control", "manage", "Manage roles and permissions"),
]

ROLE_GRANTS = {
    "admin": [(p[0], p[1]) for p in PERMISSIONS],
    "editor": [
        ("document", "read"),
        ("document", "create"),
        ("document", "update"),
        ("report", "read"),
    ],
    "viewer": [
        ("document", "read"),
        ("report", "read"),
    ],
}

ROLE_DESCRIPTIONS = {
    "admin": "Full access, including access-control management",
    "editor": "Can read and modify documents and read reports",
    "viewer": "Read-only access to documents and reports",
}

# (email, password, first, last, is_superuser, role)
USERS = [
    ("admin@example.com", "admin123", "Alice", "Admin", True, "admin"),
    ("editor@example.com", "editor123", "Ed", "Editor", False, "editor"),
    ("viewer@example.com", "viewer123", "Vic", "Viewer", False, "viewer"),
]
