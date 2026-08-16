FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages /packages
COPY products/iot/backend /app

RUN pip install --no-cache-dir \
      /packages/contracts \
      /packages/observability \
      /packages/kernel \
      .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "iot.main:app", "--host", "0.0.0.0", "--port", "8000"]
