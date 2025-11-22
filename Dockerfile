FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install system dependencies and clean up in one layer
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    git \
    && rm -rf /var/lib/apt/lists/*

# Download and install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Copy dependency files first
COPY pyproject.toml uv.lock /app/

# Install project dependencies via uv
RUN uv sync

# Copy the rest of the project
COPY . /app

# Install pre-commit hooks
RUN uv run pre-commit install-hooks

# Make entrypoint executable
RUN chmod +x /app/scripts/entrypoint.sh

# Expose Django dev server port
EXPOSE 8000

# Use entrypoint
ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]
