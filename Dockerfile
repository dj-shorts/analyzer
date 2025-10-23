# Multi-stage Dockerfile for DJ Shorts Analyzer
# Stage 1: Builder - Install dependencies and build
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
RUN pip install --no-cache-dir uv>=0.5.0

# Copy dependency files and source code for uv to build
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim

# Install system dependencies required for analyzer
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
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

