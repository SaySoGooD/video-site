# users-service

The account service of a video site. It answers exactly one question —

```
WHO IS THIS USER?
```

— and nothing else. It owns accounts, credentials, login sessions and the RBAC
model; it does not own videos, uploads, comments or analytics. Those are
separate services that ask this one who the caller is.

```
                  Browser
                 /       \
                /         \
               ▼           ▼
          users-service   Matomo
               │
               ▼
          visitor / session
               │
               ▼
         Event Collector
```

`users-service` knows *who*, an analytics service knows *what a visitor did*,
and Matomo does standard web analytics. The only thing this service does for
analytics is issue and store a **`visitor_id`** — see below.

## Tech stack

- Python 3.12+, FastAPI, uvicorn
- SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg driver)
- PyJWT for stateless access + refresh tokens
- Argon2id password hashing (argon2-cffi), PBKDF2 available as an alternative
- Optional Redis cache (falls back to a no-op cache when unset)
- dependency-injector for composition
- pydantic / pydantic-settings for schemas & config

## Authentication for a browser: HttpOnly cookies, not localStorage

The token model is unchanged — a short-lived **access token**, a long-lived
**refresh token**, and a server-side **session** row whose `jti` both tokens
carry so either can be revoked. What changed is *where the browser keeps them*:

```
Browser
   │
   │ HttpOnly cookie
   ▼
Gateway
   │
   ▼
users-service
```

- `POST /auth/login` sets `access_token` and `refresh_token` as **HttpOnly,
  Secure, SameSite** cookies. They are deliberately **absent from the response
  body** — a script on the page (including an injected one) cannot read them.
- The refresh cookie is scoped to `REFRESH_COOKIE_PATH` (`/auth`), so ordinary
  API requests never carry it.
- Because the browser now sends credentials on its own, unsafe requests are
  verified with a **double-submit CSRF token**: login returns `csrf_token` and
  sets it as a *readable* cookie; the frontend echoes it in the
  `X-CSRF-Token` header. Mismatch ⇒ **403**. A foreign site can make the
  browser send a cookie, but cannot read one.
- Set `COOKIE_AUTH_ENABLED=false` for non-browser clients (mobile, another
  service): then `login`/`refresh` return the tokens in the body and the
  client sends `Authorization: Bearer <token>`. Both modes are always accepted
  on the read path; the cookie wins when both are present.

## visitor_id — the seam to analytics

Every visitor, logged in or not, is issued an opaque `visitor_id` cookie on
first contact (UUID v4, 400 days — the browser maximum). It is **not a
credential**: it identifies a browser, not a person.

- `POST /auth/register` records the current `visitor_id` on the new account, so
  the visitor's pre-signup activity can be attributed once they sign up.
- Every login session stores the `visitor_id` it was created from.
- `GET /auth/me` returns it to the owner, which is how a frontend passes it to
  Matomo (as a custom dimension) or to the event collector.
- It never appears on a public profile.

Analytics stays outside this service: it reads the link, this service never
reports events.

## Access-control model (database schema)

Classic RBAC: **users → roles → permissions**. A permission is the atomic rule
"may perform *action* on *resource*". Users never hold permissions directly —
only through roles.

| Table              | Purpose | Key columns |
|--------------------|---------|-------------|
| `users`            | Accounts. `email` is private, `username` is the public handle. `is_active=False` is the *soft-delete* state; `is_superuser` bypasses all permission checks. `visitor_id` is the browser the account was created from. | `id` PK, `email` UNIQUE, `username` UNIQUE |
| `roles`            | Named bundles of permissions. | `id` PK, `name` UNIQUE |
| `permissions`      | Atomic rules — a `(resource, action)` pair, e.g. `account:read`. | `id` PK, UNIQUE `(resource, action)` |
| `user_roles`       | Many-to-many: which roles a user has. | composite PK `(user_id, role_id)` |
| `role_permissions` | Many-to-many: which permissions a role grants. | composite PK `(role_id, permission_id)` |
| `sessions`         | Server-side login records, one per device. Each issued JWT carries a `jti` pointing here so a token can be **revoked** (logout / soft-delete / refresh rotation). Also stores `visitor_id`, `user_agent`, `ip_address`, `last_used_at` for the "your devices" screen. | `id` PK, `jti` UNIQUE |

### How a request is decided

1. Take the access token from the auth cookie, or from `Authorization: Bearer`.
2. **No/invalid token or revoked/expired session → 401** (`AuthenticationError`).
3. Load the user (with roles + permissions). Inactive user → 401.
4. The route declares a required permission, e.g. `require_permission("account","read")`.
5. `User.has_permission(resource, action)` = superuser **or** any role grants it.
   - Granted → **200**; not granted → **403** (`AuthorizationError`).

### ACID

Each use case runs inside one **unit of work** (`SqlAlchemyUnitOfWork`) wrapping
a single database transaction. All repositories share it, so a use case's
writes commit or roll back together. Registration inserts the account *and*
grants the default role in one commit; soft-delete deactivates the user *and*
revokes every session in one commit; refresh revokes the old session *and*
writes the new one in one commit. Uniqueness of `email`, `username` and
`(resource, action)` is enforced by database constraints.

### Passwords

Stored only as salted hashes; plaintext is never persisted. The scheme is
chosen by `PASSWORD_HASHER` behind the `IPasswordHasher` port: **`argon2`**
(default, memory-hard Argon2id) or **`pbkdf2`** (PBKDF2-HMAC-SHA256, stdlib).
Switching the scheme means existing hashes of the other format no longer verify.

### Caching (optional)

If `REDIS_URL` is set, the authenticated user (with roles/permissions) is cached
to avoid a join on every request; otherwise a no-op cache is used. Security is
unaffected: the session is validated against the database on **every** request
(logout / soft-delete are immediate), and a user's cache entry is invalidated
when their roles or profile change.

## API

### Auth
- `POST /auth/register` — email/username/password/password_repeat → 201 with the
  new profile (409 duplicate email or username, 422 password mismatch)
- `POST /auth/login` — email + password → sets cookies, returns
  `{ user, csrf_token, tokens: null }` (or the tokens, in token mode); 401 on bad creds
- `POST /auth/refresh` — rotates the session; token from the cookie or the body
- `POST /auth/logout` — revoke the session and clear the cookies (204)
- `GET /auth/me` — the owner's view of the account
- `PATCH /auth/me` — update own profile (username / display name / email)
- `DELETE /auth/me` — **soft-delete**: `is_active=False` + revoke sessions (204)

### Users
- `GET /users/{id}` — public profile: id, username, display name, created_at.
  Unauthenticated; 404 for missing or soft-deleted accounts
- `PATCH /users/me` — same as `PATCH /auth/me`
- `GET /users/me/sessions` — the caller's live logins, `current: true` on the one
  the request is using
- `DELETE /users/me/sessions/{id}` — sign that device out (404 if not the caller's)

### Access-control admin API — requires `access_control:manage`
- `GET/POST /admin/permissions`
- `GET/POST /admin/roles`, `DELETE /admin/roles/{id}`
- `POST /admin/roles/{id}/permissions`, `DELETE /admin/roles/{id}/permissions/{pid}`
- `GET /admin/users`
- `POST /admin/users/{id}/roles`, `DELETE /admin/users/{id}/roles/{rid}`

## Seeded demo data

On startup (`SEED_ON_STARTUP=true`) the schema is created and demo data is
inserted **if the database is empty**.

Permissions: `account:read`, `account:moderate`, `access_control:manage`.

| Role        | Permissions |
|-------------|-------------|
| `admin`     | all (the seeded admin user is also `is_superuser`) |
| `moderator` | account read/moderate |
| `user`      | none — the default role every signup receives |

| User                    | Username    | Password       | Role      |
|-------------------------|-------------|----------------|-----------|
| `admin@example.com`     | `admin`     | `admin123`     | admin     |
| `moderator@example.com` | `moderator` | `moderator123` | moderator |
| `viewer@example.com`    | `viewer`    | `viewer123`    | user      |

## Architecture

Layered (clean) architecture; dependencies point inward only. The codebase
follows a strict **one class per file** rule — related classes are grouped in a
folder rather than a single module (small DTOs/pydantic models are the only
exception). Application ports are `ABC`s implemented by the adapters.

```
src/users_service/
├── entities/                   # Domain: User, Role, Permission, AuthSession
│   └── <entity>/               #   models.py + value_objects.py per entity
├── application/                # Use cases + ports (ABCs)
│   ├── common/
│   │   ├── errors.py           #   application error hierarchy
│   │   ├── dto.py              #   small input/output DTOs
│   │   └── interfaces/
│   │       ├── security/       #   i_password_hasher, i_token_service (+ token DTOs)
│   │       ├── repositories/   #   one repository ABC per file
│   │       └── i_unit_of_work.py
│   ├── auth/                   #   register, login, refresh, logout, authenticate,
│   │                           #   update profile, soft-delete
│   ├── users/                  #   public profile, own sessions, revoke a session
│   └── access_control/         #   roles & permissions administration
├── adapter/
│   ├── database/               #   ORM models, mappers, repositories, UoW, seed
│   ├── security/               #   Argon2 + PBKDF2 hashers, JWT token service
│   └── cache/                  #   NullCache + RedisCache
├── infrastructure/
│   ├── api/
│   │   ├── routers/            #   auth, users, admin, health
│   │   ├── models/             #   request/response schemas
│   │   ├── cookies.py          #   HttpOnly session + visitor cookies
│   │   ├── csrf_middleware.py  #   double-submit CSRF check
│   │   ├── dependencies.py     #   401/403 gates, device info
│   │   └── exc_handlers.py     #   application errors -> HTTP status codes
│   └── config.py               #   pydantic-settings Config
├── dependency_injection.py     # DI container
├── bootstrap.py                # Composition root: app factory + lifespan
└── __main__.py                 # Entry point
```

The application layer depends only on **ports** (`IUserRepository`,
`ISessionRepository`, `IUnitOfWork`, `IPasswordHasher`, `ITokenService` — all
`ABC`s in `i_*.py` files). SQLAlchemy, PyJWT and FastAPI live behind
adapters/infrastructure and never leak inward.

## Quick start

```bash
cp .env.example .env      # set DB_* and JWT_SECRET
uv sync
uv run python -m users_service
```

Open http://localhost:8001/docs

```bash
curl -c jar -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

curl -b jar http://localhost:8001/auth/me
```

## Tests

```bash
uv run pytest -q
```

`test/unit_tests/` covers pure logic (password hashing, token service, domain
permission checks). `test/integration_tests/` runs the full stack — DI
container, unit of work, repositories, use cases, routers — against an
in-memory SQLite database, so only the DB engine is swapped and PostgreSQL is
not needed for a test run. Both auth modes are exercised: `client` (bearer
tokens) and `browser` (HttpOnly cookies + CSRF).

## Not built yet

Deliberately left for later milestones: email verification, password reset,
login rate limiting / lockout, and audit events.

## License

Apache-2.0
