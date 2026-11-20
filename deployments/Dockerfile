FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY onyx/ ./onyx/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/onyx /usr/local/bin/onyx
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

COPY onyx/ ./onyx/
COPY configs/ ./configs/
COPY README.md ./

EXPOSE 8080

CMD ["onyx", "start", "--host", "0.0.0.0", "--port", "8080"]
