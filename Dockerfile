FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV SECRET_KEY=build-time-placeholder
RUN uv run python manage.py collectstatic --noinput

# --- Runtime stage ---
FROM python:3.12-slim

RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app
COPY --from=builder /app /app

RUN mkdir -p /app/generated && chown app:app /app/generated

USER app

ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE ${PORT:-8000}

CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
