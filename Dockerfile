# Multi-stage Dockerfile for NBA MCP Server
# Optimized for production use with minimal image size

# ============================================================================
# Stage 1: Builder - Install dependencies and build wheels
# ============================================================================
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy only dependency files first (for better caching)
COPY pyproject.toml README.md ./

# Install uv for faster dependency installation
RUN pip install --no-cache-dir uv

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies (without dev dependencies)
RUN uv pip install --no-cache -e .

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for some Python packages
    libgomp1 \
    # Useful for debugging
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash nbauser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=nbauser:nbauser . /app/

# Set environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Default configuration (can be overridden)
    NBA_MCP_PORT=8000 \
    NBA_MCP_LOG_LEVEL=INFO \
    ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Switch to non-root user
USER nbauser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${NBA_MCP_PORT}/health || exit 1

# Default command - run server
CMD ["nba-mcp", "serve", "--mode", "local"]
