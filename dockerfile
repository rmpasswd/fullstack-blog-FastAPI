# BUILD STAGE
# FROM python:3.14.4-slim-bookworm AS builder
FROM python:3.9-alpine3.22 AS builder

# Copy UV binary from official image
# COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/
COPY --from=ghcr.io/astral-sh/uv:0.11.11-python3.10-trixie@sha256:71cdc5bd300420d15d638b86c54bf653de0d5d9d54919fbc66af05e1a1367e3a  /uv /uvx /bin/
WORKDIR /app

# UV Docker optimizations
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

# Install dependencies first (cached if unchanged)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

# Copy app code and install project
COPY . ./
RUN uv sync --locked --no-dev

# PRODUCTION STAGE
# FROM python:3.14.4-slim-bookworm
FROM python:3.9-alpine3.22


WORKDIR /app

# Copy app and dependencies from builder stage
COPY --from=builder --chown=appuser:appuser /app /app

# Run as non-root user for security
# RUN useradd -m appuser && chown -R appuser:appuser /app  # alpine ec2 instace do support useradd but docker's alpine image does not
RUN adduser -D -s /sbin/nologin appuser && chown -R appuser:appuser /app
# user with  no pass and login permission.

USER appuser


ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# exec replaces shell so fastapi receives SIGTERM for clean shutdown
CMD ["/bin/sh", "-c", "exec fastapi run --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips '*'"]





