# auth-test

A custom **authentication & authorization** backend built from scratch — the
framework's built-in auth is deliberately *not* used. It implements its own
user lifecycle, JWT/session handling, and a **role-based access control
(RBAC)** model whose rules live in the database and can be edited at runtime by
an administrator.


## Tech stack

- Python 3.12+, FastAPI, uvicorn
- SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg driver)
- PyJWT for stateless access + refresh tokens
- Argon2id password hashing (argon2-cffi), PBKDF2 available as an alternative
- Optional Redis cache (falls back to a no-op cache when unset)
- dependency-injector for composition
- pydantic / pydantic-settings for schemas & config

## Authentication vs. authorization

- **Authentication** — *who are you?* Handled by login (email + password →
  signed JWT) and by resolving that token on every request. Failure ⇒ **401**.
- **Authorization** — *are you allowed?* Handled by the RBAC model below: a
  user's roles are checked against the permission a route requires. Failure ⇒
  **403**.

## Access-control model (database schema)

The model is classic RBAC: **users → roles → permissions**. A permission is the
atomic rule "may perform *action* on *resource*". Users never hold permissions
directly — only through roles — which keeps the rules small and manageable.


### Tables

| Table              | Purpose | Key columns |
|--------------------|---------|-------------|
| `users`            | Accounts. `is_active=False` is the *soft-delete* state. `is_superuser` bypasses all permission checks. | `id` PK, `email` UNIQUE |
| `roles`            | Named bundles of permissions. | `id` PK, `name` UNIQUE |
| `permissions`      | Atomic rules — a `(resource, action)` pair, e.g. `document:read`. | `id` PK, UNIQUE `(resource, action)` |
| `user_roles`       | Many-to-many: which roles a user has. | composite PK `(user_id, role_id)` |
| `role_permissions` | Many-to-many: which permissions a role grants. | composite PK `(role_id, permission_id)` |
| `sessions`         | Server-side login records. Each issued JWT carries a `jti` pointing here so a token can be **revoked** (logout / soft-delete). | `id` PK, `jti` UNIQUE |

### How a request is decided

1. Extract the `Authorization: Bearer <jwt>` token.
2. **No/invalid token or revoked/expired session → 401** (`AuthenticationError`).
3. Load the user (with roles + permissions). Inactive user → 401.
4. The route declares a required permission, e.g. `require_permission("document","read")`.
5. `User.has_permission(resource, action)` = superuser **or** any role grants it.
   - Granted → **200** with the resource.
   - Not granted → **403** (`AuthorizationError`).

### Normalization

- **1NF** — every column holds a single atomic value; there are no repeating
  groups (a user's multiple roles are rows in `user_roles`, not a list column).
- **2NF** — every table has a key and no non-key column depends on only part of
  a composite key. The junction tables (`user_roles`, `role_permissions`) are
  pure keys with no other attributes, so no partial dependency can exist;
  descriptive attributes live on `users`, `roles`, `permissions` where they
  depend on the whole (single-column) key.

### ACID

Each use case runs inside one **unit of work** (`SqlAlchemyUnitOfWork`) that
wraps a single database transaction. All repositories share that transaction,
so a use case's writes **commit or roll back together** (atomicity,
consistency). For example, soft-delete deactivates the user *and* revokes every
session in one commit — a user is never left half-deleted. Uniqueness of emails
and `(resource, action)` is enforced by database constraints (isolation +
durability come from PostgreSQL).

### Passwords

Passwords are stored only as salted hashes; plaintext is never persisted. The
scheme is chosen by `PASSWORD_HASHER` behind the `IPasswordHasher` port:

- **`argon2`** (default) — Argon2id via argon2-cffi; memory-hard, resistant to
  GPU/ASIC brute force. Parameters and salt are embedded in the hash string.
- **`pbkdf2`** — PBKDF2-HMAC-SHA256 (standard library),
  `pbkdf2_sha256$iterations$salt$hash`, constant-time verification.

Switching the scheme means existing hashes of the other format no longer verify
(re-seed or reset passwords).

### Caching (optional)

If `REDIS_URL` is set, the authenticated user (with roles/permissions) is cached
in Redis to avoid a join on every request; otherwise a no-op cache is used and
Redis is not required. Behind the `ICache` port (`NullCache` / `RedisCache`).
Security is unaffected: the session is validated against the database on every
request (logout / soft-delete are immediate), and a user's cache entry is
invalidated when their roles or profile change. Role↔permission edits converge
within `AUTH_CACHE_TTL_SECONDS` (default 30).

## Seeded demo data

On startup (when `SEED_ON_STARTUP=true`) the schema is created and demo data is
inserted **if the database is empty**.

Permissions: `document:read|create|update|delete`, `report:read|export`,
`access_control:manage`.

| Role     | Permissions |
|----------|-------------|
| `admin`  | all (user also flagged `is_superuser`) |
| `editor` | document read/create/update, report read |
| `viewer` | document read, report read |

| User                 | Password    | Role   |
|----------------------|-------------|--------|
| `admin@example.com`  | `admin123`  | admin  |
| `editor@example.com` | `editor123` | editor |
| `viewer@example.com` | `viewer123` | viewer |

## API

### Users & auth (module 1)
- `POST /auth/register` — name/email/password/password_repeat → creates active account (409 duplicate, 422 mismatch)
- `POST /auth/login` — email + password → `{ access_token, refresh_token, ... }` (401 on bad creds)
- `POST /auth/refresh` — swap a valid refresh token for a new pair (rotates it; 401 if invalid)
- `POST /auth/logout` — revoke current session (204)
- `GET /auth/me` — current profile
- `PATCH /auth/me` — update own profile
- `DELETE /auth/me` — **soft-delete**: `is_active=False` + revoke sessions (204)

### Access-control admin API (module 2) — requires `access_control:manage`
- `GET/POST /admin/permissions`
- `GET/POST /admin/roles`, `DELETE /admin/roles/{id}`
- `POST /admin/roles/{id}/permissions`, `DELETE /admin/roles/{id}/permissions/{pid}`
- `GET /admin/users`
- `POST /admin/users/{id}/roles`, `DELETE /admin/users/{id}/roles/{rid}`

### Mock business objects (module 3) — protected by permissions
- `GET/POST /documents`, `PUT/DELETE /documents/{id}`
- `GET /reports`, `POST /reports/export`

Each returns mock data on success, or 401 / 403 per the rules above.

## Architecture

Layered (clean) architecture; dependencies point inward only. The codebase
follows a strict **one class per file** rule — related classes are grouped in a
folder rather than a single module (small DTOs/pydantic models are the only
exception). Application ports are `ABC`s implemented by the adapters.

```
src/auth_test/
├── entities/                   # Domain: User, Role, Permission, AuthSession
│   └── <entity>/               #   models.py + value_objects.py per entity
├── application/                # Use cases + ports (ABCs)
│   ├── common/
│   │   ├── errors.py           #   application error hierarchy
│   │   ├── dto.py              #   small input/output DTOs
│   │   └── interfaces/
│   │       ├── security/       #   i_password_hasher, i_token_service (+ token DTOs)
│   │       ├── repositories/   #   one repository ABC per file
│   │       └── unit_of_work.py
│   ├── auth/
│   │   ├── interfaces/         #   one I*UseCase ABC per file
│   │   └── usecases/           #   one use case per file
│   └── access_control/
│       ├── interfaces/         #   one I*UseCase ABC per file
│       └── usecases/           #   one use case per file
├── adapter/
│   ├── database/
│   │   ├── base.py             #   DeclarativeBase + association tables
│   │   ├── orm_models/         #   one ORM model per file
│   │   ├── mappers/            #   one ORM->entity mapper per file
│   │   ├── repositories/       #   one repository implementation per file
│   │   ├── unit_of_work.py
│   │   └── seed.py             #   schema creation + demo data
│   ├── memory/                 #   in-memory mock DB (MOCK_DB=True)
│   ├── security/               #   Argon2 + PBKDF2 hashers, JWT token service
│   └── cache/                  #   NullCache + RedisCache
├── infrastructure/
│   ├── api/                    #   routers, request/response models,
│   │                           #   dependencies (401/403), exception handlers
│   └── config.py               #   pydantic-settings Config
├── dependency_injection.py     # DI container
├── bootstrap.py                # Composition root: app factory + lifespan
└── __main__.py                 # Entry point
```

The application layer depends only on **ports** (`IUserRepository`,
`IUnitOfWork`, `IPasswordHasher`, `ITokenService` — all `ABC`s, named with an
`I` prefix in `i_*.py` files). SQLAlchemy,
PyJWT and FastAPI live behind adapters/infrastructure and never leak inward.

## Database backends

`MOCK_DB` selects where data lives, without touching any other layer (the app
depends only on the `UnitOfWork` / repository ports):

- **`MOCK_DB=True`** (default) — an in-memory mock (`adapter/memory/`). No
  server to install; data lives in process and resets on restart. Ideal for
  demos/tests.
- **`MOCK_DB=False`** — the real SQLAlchemy + PostgreSQL backend
  (`adapter/database/`), using the `DB_*` settings.

## Quick start

```bash
cd auth_test
uv sync
uv run python -m auth_test          # MOCK_DB=True by default — no DB needed
```

To use PostgreSQL instead:

```bash
cp .env.example .env                # set MOCK_DB=False, DB_* and JWT_SECRET
uv run python -m auth_test
```

Open http://localhost:8001/docs

Example:
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

curl http://localhost:8001/admin/roles -H "Authorization: Bearer <token>"
```

## Tests

```bash
uv run pytest -q
```

Tests are split into `test/unit_tests/` (pure logic: password hashing, token
service, domain permission checks) and `test/integration_tests/` (the full
application stack against an in-memory SQLite database — only the DB engine is
overridden, so PostgreSQL is not required). Each test file groups its cases in
a class.

## License

Apache-2.0
