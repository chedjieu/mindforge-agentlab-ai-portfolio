FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8002 \
    EGKP_MODEL=fake \
    EGKP_EMBEDDINGS=fake

COPY pyproject.toml uv.lock ./
COPY app ./app
COPY data ./data
COPY evals ./evals
COPY security ./security

RUN uv sync --frozen --no-dev

EXPOSE 8002

CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
