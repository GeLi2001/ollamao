# Multi-stage build for production-ready Docker image
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r ollamao && useradd -r -g ollamao ollamao

# Set work directory
WORKDIR /app

# Copy requirements and project config
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY config/ config/

# Install the package in development mode
RUN pip install -e .

# Change ownership to non-root user
RUN chown -R ollamao:ollamao /app

# Switch to non-root user
USER ollamao

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "ollamao.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

USER root
RUN pip install -e ".[dev]"
USER ollamao

CMD ["uvicorn", "ollamao.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage  
FROM base as production

# Use gunicorn for production
CMD ["gunicorn", "ollamao.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
