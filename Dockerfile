# Build and run the services of this repository.
#
# Multi-stage so the runtime image carries the virtualenv and the source, but
# none of the build tooling. uv installs from the lockfile, so an image built
# today and one built next month contain the same dependency versions.
#
# One image serves every service: they share a project and differ only by the
# module they run, which compose and Kubernetes choose with the command.

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer is cached until the lockfile itself changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev


FROM python:3.12-slim AS runtime

# Never run a service as root.
RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_PORT=8001

USER app

# 8000 is the gateway, 8001 users-service.
EXPOSE 8000 8001

# SERVICE_PORT follows whichever service the command started.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request,sys; url='http://127.0.0.1:'+os.environ['SERVICE_PORT']+'/health'; sys.exit(0 if urllib.request.urlopen(url).status == 200 else 1)"

# The default is users-service; the gateway overrides this command.
# No --reload here; that belongs to development only.
CMD ["uvicorn", "users_service.bootstrap:bootstrap", "--factory", \
     "--host", "0.0.0.0", "--port", "8001"]
