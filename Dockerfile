FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY rubric.json ./
COPY reports ./reports
COPY audit ./audit

RUN uv sync --frozen

ENTRYPOINT ["uv", "run", "automation-auditor"]

