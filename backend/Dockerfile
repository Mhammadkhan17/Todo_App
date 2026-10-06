# Multi-stage Dockerfile for FastAPI Todo Application
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: Production stage (MUST BE THE LAST STAGE FOR HUGGING FACE)
FROM python:3.11-slim as production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y libpq5 curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# HF expects UID 1000
RUN useradd -m -u 1000 appuser
WORKDIR /home/appuser/app

# Copy application code
COPY . .

# Ensure permissions are correct
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

# Hugging Face requirement
EXPOSE 7860

# Increased start-period to 15s to allow for DB connection and table creation
HEALTHCHECK --interval=30s --timeout=30s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Ensure the app binds to all interfaces and the HF required port with proxy support
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips='*'", "--log-level", "info"]