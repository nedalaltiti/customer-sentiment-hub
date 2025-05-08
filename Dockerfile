# Base stage for dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set up the working directory
WORKDIR /app

# Copy only requirements files to cache dependencies
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --only main --no-interaction --no-ansi

# Final stage with just the runtime dependencies
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY src/ /app/src/
COPY README.md /app/

# Create log directory with proper permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Create a non-root user for better security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Run the FastAPI application with uvicorn directly
# This is the key change to fix the startup issues
CMD ["uvicorn", "customer_sentiment_hub.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]