# Dockerfile for API Governance Agent
# Multi-stage build for optimized image size

FROM node:18-alpine AS spectral-builder

# Install Spectral CLI
RUN npm install -g @stoplight/spectral-cli@6.11.0

FROM python:3.11-slim

# Install Node.js and npm (for Spectral)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Spectral from builder
COPY --from=spectral-builder /usr/local/lib/node_modules/@stoplight/spectral-cli /usr/local/lib/node_modules/@stoplight/spectral-cli
COPY --from=spectral-builder /usr/local/bin/spectral /usr/local/bin/spectral

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY rules/ ./rules/
COPY cli/ ./cli/

# Create directory for project mounting
RUN mkdir -p /project

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
ENTRYPOINT ["python",  "/app/src/main.py"]
CMD ["scan", "--project", "/project"]