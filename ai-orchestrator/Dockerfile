ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11
FROM node:20-alpine AS frontend-builder

# Build React dashboard
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci --only=production
COPY dashboard/ ./
RUN npm run build

# Runtime stage
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    curl \
    bash \
    jq

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /app/backend/requirements.txt

# Copy backend application
COPY backend/ /app/backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/dashboard/dist /app/dashboard/dist

# Install Ollama CLI (for model management)
RUN curl -fsSL https://ollama.com/install.sh | sh || echo "Ollama install skipped, will use external server"

# Create data directory for persistent storage
RUN mkdir -p /data/decisions

# Copy entrypoint script
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose ports
EXPOSE 8099

# Labels for Home Assistant
ARG BUILD_VERSION
LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="addon" \
      io.hass.name="AI Orchestrator" \
      io.hass.description="Phase 6: Universal Agents, RAG, and No-Code Factory" \
      io.hass.arch="amd64|armv7|aarch64"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8099/api/health || exit 1

# Run entrypoint
CMD ["/app/run.sh"]
