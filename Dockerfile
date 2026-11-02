# ============================================================================
# Multi-Stage Production Dockerfile for AgriNova / Krishi Mitra Backend
# ============================================================================

# Stage 1: Build & Dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# Stage 2: Minimal Production Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8000

# Install runtime C libraries for PostgreSQL/GIS connectivity and curl for health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Create non-privileged system user for OWASP container security
RUN groupadd -g 10001 agriuser && \
    useradd -u 10001 -g agriuser -s /bin/bash -m agriuser

# Copy application source code
COPY backend/ /app/backend/
COPY storage/ /app/storage/

# Set file ownership
RUN chown -R agriuser:agriuser /app

USER agriuser

EXPOSE 8000

# Process liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-config", "backend/app/core/logging.py"]

