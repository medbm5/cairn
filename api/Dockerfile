# syntax=docker/dockerfile:1

# --- build stage: resolve dependencies into a virtualenv with uv ---
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# --- runtime stage: slim image, non-root user ---
FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 10001 cairn
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER cairn
EXPOSE 8000
CMD ["uvicorn", "cairn.main:app", "--host", "0.0.0.0", "--port", "8000"]
