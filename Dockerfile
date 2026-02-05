# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies
FROM base AS dependencies

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Build stage
FROM base AS builder

# Copy dependencies from previous stage
COPY --from=dependencies /app/.venv /app/.venv

# Copy application code
COPY api/ ./api/
COPY core/ ./core/
COPY providers/ ./providers/
COPY catalog/ ./catalog/
COPY kb/ ./kb/
COPY pyproject.toml uv.lock ./

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/api ./api
COPY --from=builder /app/core ./core
COPY --from=builder /app/providers ./providers
COPY --from=builder /app/catalog ./catalog
COPY --from=builder /app/kb ./kb

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
