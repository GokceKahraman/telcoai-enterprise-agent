# syntax=docker/dockerfile:1.7
FROM python:3.12.15-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
ARG UV_EXTRAS=""
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -n "$UV_EXTRAS" ]; then \
      uv sync --frozen --no-dev --extra "$UV_EXTRAS"; \
    else \
      uv sync --frozen --no-dev; \
    fi

FROM python:3.12.15-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    HF_HOME="/home/app/.cache/huggingface" \
    FASTEMBED_CACHE_PATH="/home/app/.cache/fastembed" \
    TELCOAI_RETRIEVAL_STRATEGY=keyword \
    TELCOAI_STORAGE_BACKEND=memory
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=app:app app ./app
COPY --chown=app:app data ./data
COPY --chown=app:app static ./static
COPY --chown=app:app scripts ./scripts
RUN mkdir -p /app/artifacts /home/app/.cache && chown app:app /app/artifacts /home/app/.cache
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
