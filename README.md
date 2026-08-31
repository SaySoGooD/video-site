# video-site

The backend of a video site. Right now it contains one service.

## users-service

It answers exactly one question —

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
- SQLAlchemy 2.0 (async) + PostgreSQL (asyncpg), schema managed by Alembic
- PyJWT for stateless access + refresh tokens
- Argon2id password hashing (argon2-cffi), PBKDF2 available as an alternative
- Redis for the auth cache and rate limiting
- dependency-injector for composition
- pydantic / pydantic-settings for schemas & config

## Authentication for a browser: HttpOnly cookies, not localStorage

The token model is the usual one — a short-lived **access token**, a long-lived
**refresh token**, and a server-side **session** row whose `jti` both tokens
carry so either can be revoked. What matters is *where the browser keeps them*:

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
- The refresh cookie is scoped to `REFRESH_COOKIE_PATH`, so ordinary API
  requests never carry it.
- Because the browser now sends credentials on its own, unsafe requests are
  verified with a **double-submit CSRF token**: login returns `csrf_token` and
  sets it as a *readable* cookie; the frontend echoes it in the
  `X-CSRF-Token` header. Mismatch ⇒ **403**. A foreign site can make the
  browser send a cookie, but cannot read one.
- Refresh **rotates**: the presented session is revoked and a new one issued in
  the same transaction, so a stolen refresh token replayed after the real
  client has refreshed fails with 401 and surfaces the theft.
- Set `COOKIE_AUTH_ENABLED=false` for non-browser clients (mobile, another
  service): `login`/`refresh` then return the tokens in the body and the client
  sends `Authorization: Bearer <token>`. Both are accepted on the read path;
  the cookie wins when both are present.

## visitor_id — the seam to analytics

Every visitor gets an opaque `visitor_id` cookie on first contact — issued by
middleware, so it is handed out on *every* response, including 401s and 404s.
It exists **before** there is a user, which is the whole point:

```
anonymous visitor
       │
       ▼
visitor_id = UUID
       │
       ├── page views
       ├── content views
       └── sessions
       │
       ▼
     REGISTER
       │
       ▼
   user_id = 123
```

`visitor_id ≠ user_id`. It identifies a browser, not a person, and is never a
credential — nothing is authorized on the strength of it.

- `POST /auth/register` records the current `visitor_id` on the new account,
  which is what ties pre-signup activity to it.
- Every login session stores the `visitor_id` it was created from, so one
  account accumulates the browsers it has been used from.
- `GET /users/me` returns it to the owner; that is how a frontend passes it to
  Matomo (as a custom dimension) or to the event collector.
- It never appears on a public profile.

## Account security

| Concern | How it is handled |
|---|---|
| Password storage | Argon2id, salt and parameters embedded in the hash |
| Brute force | Per-IP **and** per-account counters — a botnet spread over thousands of IPs still cannot grind one account |
| Lockout | Exceeding the per-account limit locks it for the rest of the window (default 5 / 15 min); a successful login clears the counter |
| Email verification | One-time token, **stored only as a SHA-256 hash**; changing the email un-verifies the account and re-sends |
| Password reset | Same token machinery, 30-minute expiry, single use — and completing it **revokes every session** |
| Enumeration | Bad password and unknown account return the same 401; `forgot-password` answers identically for known and unknown addresses |
| Audit | Every event below is appended in the same transaction as the action it records |

Audit actions: `REGISTER`, `LOGIN`, `LOGIN_FAILED`, `LOGOUT`,
`PASSWORD_CHANGED`, `PASSWORD_RESET`, `EMAIL_VERIFIED`, `SESSION_REVOKED`,
`USER_BANNED`, `USER_UNBANNED`.

## API

Everything below is mounted under `API_PREFIX` (`/api/v1`). Health probes are
unversioned.

### Auth
- `POST /auth/register` — email/username/password/password_repeat → 201 with the
  profile; mails a verification link (409 duplicate, 422 mismatch, 429 flood)
- `POST /auth/login` — → sets cookies, returns `{ user, csrf_token, tokens: null }`
  (or the tokens in token mode); 401 bad creds, 429 locked out
- `POST /auth/refresh` — rotates the session; token from cookie or body
- `POST /auth/logout` — revoke this session, clear the cookies (204)
- `GET  /auth/me` — the caller's account
- `GET  /auth/verify-email?token=…` — confirm an address (400 if spent/expired)
- `POST /auth/forgot-password` — mail a reset link; always the same answer
- `POST /auth/reset-password` — set a new password, sign every device out

### Users
- `GET    /users/me` — own account (email, verification state, roles, permissions)
- `PATCH  /users/me` — update username / display name / email
- `DELETE /users/me` — soft-delete: deactivate + revoke every session (204)
- `GET    /users/me/sessions` — live logins, `current: true` on this one
- `DELETE /users/me/sessions/{id}` — sign that device out (404 if not yours)
- `DELETE /users/me/sessions?keep_current=true` — log out from all devices;
  `keep_current` spares the caller's own
- `GET    /users/{id}` — public profile: id, username, display name, created_at

### Moderation — requires `users.ban`
- `POST   /admin/users/{id}/ban` — deactivate an account and revoke its sessions
  (optional `reason` goes into the audit row); 403 for a superuser target,
  422 for your own account
- `DELETE /admin/users/{id}/ban` — reactivate it; the old sessions stay revoked

### Admin — requires `users.manage`
- `GET/POST /admin/permissions`
- `GET/POST /admin/roles`, `DELETE /admin/roles/{id}`
- `POST /admin/roles/{id}/permissions`, `DELETE /admin/roles/{id}/permissions/{pid}`
- `GET /admin/users`
- `POST /admin/users/{id}/roles`, `DELETE /admin/users/{id}/roles/{rid}`

### Probes
- `GET /health` — liveness: the process is up, nothing else is touched
- `GET /health/ready` — readiness: 503 if the database is unreachable

## Data model

Classic RBAC: **users → roles → permissions**. Users never hold permissions
directly — only through roles.

| Table | Purpose |
|---|---|
| `users` | Accounts. `email` private, `username` the public handle. `is_active=False` is the soft-delete state, `email_verified_at` the confirmation timestamp, `visitor_id` the browser it signed up from |
| `roles`, `permissions` | The RBAC vocabulary; a permission is a `(resource, action)` pair rendered as `content.read` |
| `user_roles`, `role_permissions` | Many-to-many links, pure keys |
| `sessions` | One row per login per device: `jti`, expiry, `revoked_at`, plus `visitor_id`, `user_agent`, `ip_address`, `device`, `last_seen_at` |
| `security_tokens` | One-time email/reset secrets, stored as hashes with `purpose` and `used_at` |
| `audit_logs` | Append-only security events with JSON metadata |

**Session status is derived, never stored**: `revoked_at` and `expires_at`
decide whether a session is active, expired or revoked, so the two can never
disagree.

### ACID

Each use case runs inside one unit of work wrapping a single transaction.
Registration inserts the account, grants the default role, mints the
verification token and writes the audit row together. A password reset changes
the hash, spends the token, revokes the sessions and records the event
together. The verification email is sent *after* the commit — mail is the one
step that can fail slowly, and a signup must not be rolled back because a mail
server hiccuped.

## Seeded demo data

With `SEED_ON_STARTUP=true` the schema is created and demo data inserted if the
database is empty.

Permissions: `content.read`, `content.moderate`, `users.read`, `users.ban`,
`users.manage`.

| Role | Permissions |
|---|---|
| `admin` | all (the seeded admin is also `is_superuser`) |
| `moderator` | content read/moderate, users read/ban |
| `user` | `content.read` — the default role every signup receives |

| User | Username | Password | Role |
|---|---|---|---|
| `admin@example.com` | `admin` | `admin123` | admin |
| `moderator@example.com` | `moderator` | `moderator123` | moderator |
| `viewer@example.com` | `viewer` | `viewer123` | user |

## Architecture

Layered (clean) architecture; dependencies point inward only. One class per
file — related classes are grouped in a folder rather than a module (small
DTOs and pydantic models are the exception). Application ports are `ABC`s
implemented by adapters.

```
src/users_service/
├── entities/                   # User, Role, Permission, AuthSession,
│                               # SecurityToken, AuditEvent
├── application/                # Use cases + ports (ABCs)
│   ├── common/                 #   errors, DTOs, audit helper, rate policy
│   ├── auth/                   #   register, login, refresh, logout, verify,
│   │                           #   forgot/reset password, profile, delete
│   ├── users/                  #   public profile, sessions, revoke (one/all)
│   └── access_control/         #   roles & permissions administration
├── adapter/
│   ├── database/               #   ORM models, mappers, repositories, UoW, seed
│   ├── security/               #   Argon2/PBKDF2, JWT, one-time tokens
│   ├── email/                  #   console + SMTP senders
│   ├── rate_limit/             #   Redis + in-process limiters
│   └── cache/                  #   NullCache + RedisCache
├── infrastructure/
│   ├── api/                    #   routers, schemas, cookies, CSRF + visitor
│   │                           #   middleware, dependencies, error mapping
│   └── config.py               #   settings + production safety checks
├── dependency_injection.py
└── bootstrap.py
```

SQLAlchemy, PyJWT, Redis, smtplib and FastAPI all live behind
adapters/infrastructure and never leak inward.

## Quick start

Docker, everything included:

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

Compose waits for PostgreSQL and Redis to report healthy, applies the Alembic
migrations, then serves on http://localhost:8001/docs.

Without Docker:

```bash
uv sync
```

```bash
uv run alembic upgrade head
```

```bash
uv run python -m users_service
```

Log in and use the cookie jar:

```bash
curl -c jar -X POST http://localhost:8001/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"admin123"}'
```

```bash
curl -b jar http://localhost:8001/api/v1/users/me
```

## Migrations

Alembic owns the schema. `SEED_ON_STARTUP` is a development convenience and is
refused in production, so the two never both create tables.

```bash
uv run alembic revision --autogenerate -m "what changed"
```

```bash
uv run alembic upgrade head
```

## Tests

```bash
uv run pytest -q
```

`test/unit_tests/` covers pure logic (hashers, token service, rate limiter,
domain permissions, production config validation). `test/integration_tests/`
runs the full stack — container, unit of work, repositories, use cases,
routers — against in-memory SQLite, so no PostgreSQL or Redis is needed for a
test run. Both auth modes are exercised: `client` (bearer) and `browser`
(cookies + CSRF), and a recording email sender lets tests read verification and
reset links the way a user would read their inbox.

## Production checklist

`ENVIRONMENT=production` refuses to start unless all of these hold, because
every one of them is silent at runtime:

- `JWT_SECRET` set and at least 32 characters
- `COOKIE_SECURE=true` and `CSRF_PROTECTION=true` (with cookie auth)
- `EMAIL_BACKEND=smtp` — otherwise reset links go to the log
- `RATE_LIMIT_ENABLED=true` and `REDIS_URL` set, so limits hold across workers
- `SEED_ON_STARTUP=false`

## Not built yet

Two-factor auth, and changing a password from inside a session
(`PASSWORD_CHANGED` is in the audit vocabulary, the endpoint is not).

Hard deletion is deliberately absent, not merely unwritten: what happens to a
deleted account's uploads and comments is a product decision, and `is_active`
plus a revoked session list already stops the account being used. Audit rows
outlive the account by design — `user_id` is `ON DELETE SET NULL`, so the event
survives while the identity does not.

## License

Apache-2.0
