# Multi-stage Dockerfile for DJ Shorts Analyzer
# Stage 1: Builder - Install dependencies and build
FROM python:3.11-slim-bookworm AS builder

# Set working directory
WORKDIR /build

# Install build dependencies for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management and update pip to latest version
RUN pip install --no-cache-dir --upgrade pip uv>=0.5.0

# Copy dependency files and source code for uv to build
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim-bookworm

# Install system dependencies required for analyzer
# Update to latest versions for security patches
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libsndfile1 \
    libxslt1.1 \
    libxml2 \
    && apt-get upgrade -y \
    && apt-get dist-upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r analyzer && useradd -r -g analyzer analyzer

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY src/ /app/src/
COPY schemas/ /app/schemas/
COPY pyproject.toml /app/

# Set ownership to non-root user
RUN chown -R analyzer:analyzer /app

# Set security-focused environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Switch to non-root user
USER analyzer

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Health check - verify analyzer can be imported
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import analyzer; print('OK')" || exit 1

# Default command - show help
CMD ["python", "-m", "analyzer.cli", "--help"]

