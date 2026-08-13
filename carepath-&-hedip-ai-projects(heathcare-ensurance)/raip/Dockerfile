FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RAIP_MODEL=fake

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY app ./app
COPY sample_data ./sample_data
COPY evals ./evals
COPY security ./security
COPY scripts ./scripts
COPY docs ./docs

RUN uv sync --python 3.12 --no-dev

EXPOSE 8011
CMD ["uv", "run", "python", "-m", "app.main"]
