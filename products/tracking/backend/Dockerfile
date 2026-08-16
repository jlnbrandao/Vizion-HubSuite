FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages /packages
COPY products/tracking/backend /app

RUN pip install --no-cache-dir \
      /packages/contracts \
      /packages/observability \
      /packages/kernel \
      /packages/events \
      . \
    && chmod +x /app/docker/entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
