FROM python:3.13-slim-bookworm

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install necessary system dependencies
# We keep curl and ca-certificates for uv installation
# Also adding build-essential and python3-dev for potential package compilation needs
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and install uv
ADD https://astral.sh/uv/0.5.15/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set up working directory
WORKDIR /app

# Copy dependency files first
# This helps with Docker layer caching - if dependencies don't change,
# Docker can reuse the cached layer
COPY pyproject.toml /app/

# Install dependencies using uv
RUN uv sync

# Copy the rest of the application code
# We do this after installing dependencies to leverage Docker's layer caching
COPY . /app/

# Set Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Run the application using gunicorn
CMD ["uv", "run", "gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]