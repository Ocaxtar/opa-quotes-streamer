# Multi-stage build for opa-quotes-streamer
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.7.1

# Copy only dependency files first (layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies without dev packages
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/
COPY shared/ ./shared/

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Copy installed packages from builder
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=base /app/src ./src
COPY --from=base /app/shared ./shared

# Create non-root user
RUN useradd -m -u 1000 streamer && \
    chown -R streamer:streamer /app

USER streamer

# Environment variables (overridable)
ENV PYTHONUNBUFFERED=1 \
    TICKERS="AAPL,MSFT,GOOGL,AMZN,TSLA" \
    POLLING_INTERVAL=5 \
    STORAGE_API_URL="http://localhost:8000" \
    MAX_REQUESTS_PER_HOUR=2000 \
    METRICS_PORT=8001 \
    LOG_LEVEL="INFO"

# Expose Prometheus metrics port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/metrics')" || exit 1

# Run the streamer
CMD ["python", "-m", "opa_quotes_streamer.main"]

