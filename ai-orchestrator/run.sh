#!/usr/bin/env bash
set -e

echo "=========================================="
echo "AI Orchestrator - Starting up"
echo "=========================================="

# Parse add-on configuration
CONFIG_PATH="/data/options.json"

if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: Configuration file not found at $CONFIG_PATH"
    exit 1
fi

# Extract configuration values
export OLLAMA_HOST=$(jq -r '.ollama_host // "http://localhost:11434"' $CONFIG_PATH)
export DRY_RUN_MODE=$(jq -r '.dry_run_mode // true' $CONFIG_PATH)
export LOG_LEVEL=$(jq -r '.log_level // "info"' $CONFIG_PATH | tr '[:lower:]' '[:upper:]')
export ORCHESTRATOR_MODEL=$(jq -r '.orchestrator_model // "deepseek-r1:8b"' $CONFIG_PATH)
export SMART_MODEL=$(jq -r '.smart_model // "deepseek-r1:8b"' $CONFIG_PATH)
export FAST_MODEL=$(jq -r '.fast_model // "mistral:7b-instruct"' $CONFIG_PATH)
export DECISION_INTERVAL=$(jq -r '.decision_interval // 120' $CONFIG_PATH)
export ENABLE_GPU=$(jq -r '.enable_gpu // false' $CONFIG_PATH)

# Security Controls
export ALLOWED_DOMAINS=$(jq -r '.allowed_domains // ""' $CONFIG_PATH)
export BLOCKED_DOMAINS=$(jq -r '.blocked_domains // ""' $CONFIG_PATH)
export HIGH_IMPACT_SERVICES=$(jq -r '.high_impact_services // ""' $CONFIG_PATH)
export MIN_TEMP=$(jq -r '.min_temp // 10.0' $CONFIG_PATH)
export MAX_TEMP=$(jq -r '.max_temp // 30.0' $CONFIG_PATH)
export MAX_TEMP_CHANGE=$(jq -r '.max_temp_change // 3.0' $CONFIG_PATH)

# Home Assistant API configuration
# Home Assistant API configuration
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"
export HA_ACCESS_TOKEN=$(jq -r '.ha_access_token // ""' $CONFIG_PATH)
export HA_URL="http://supervisor/core"

echo "Configuration loaded:"
echo "  Ollama Host: $OLLAMA_HOST"
echo "  Dry Run Mode: $DRY_RUN_MODE"
echo "  Log Level: $LOG_LEVEL"
echo "  Orchestrator Model: $ORCHESTRATOR_MODEL"
echo "  Smart Model: $SMART_MODEL"
echo "  Fast Model: $FAST_MODEL"
echo "  Decision Interval: ${DECISION_INTERVAL}s"
echo "  GPU Enabled: $ENABLE_GPU"
if [ -n "$HA_ACCESS_TOKEN" ]; then
    echo "  HA Access Token: PROVIDED (Length: ${#HA_ACCESS_TOKEN})"
    # Switch to Direct Core Access to bypass Supervisor Proxy issues
    export HA_URL="http://homeassistant:8123"
    echo "  > Switching to Direct Core Access: $HA_URL"
else
    echo "  HA Access Token: NOT PROVIDED (Using Supervisor Token fallback)"
fi

# Start Ollama server if using localhost
if [[ "$OLLAMA_HOST" == *"localhost"* ]] || [[ "$OLLAMA_HOST" == *"127.0.0.1"* ]]; then
    echo "=========================================="
    echo "Starting Ollama server..."
    echo "=========================================="
    
    # Set GPU support if enabled
    if [ "$ENABLE_GPU" = "true" ]; then
        export OLLAMA_GPU=1
        echo "GPU support enabled"
    fi
    
    # Start Ollama in background
    ollama serve &
    OLLAMA_PID=$!
    
    # Wait for Ollama to be ready
    echo "Waiting for Ollama to start..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
            echo "Ollama is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "ERROR: Ollama failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    # Pull heating model if not present
    echo "=========================================="
    echo "Checking for model: $HEATING_MODEL"
    echo "=========================================="
    
    if ! ollama list | grep -q "${SMART_MODEL%%:*}"; then
        echo "Smart Model not found. Pulling $SMART_MODEL..."
        ollama pull "$SMART_MODEL"
    fi

    if ! ollama list | grep -q "${FAST_MODEL%%:*}"; then
        echo "Fast Model not found. Pulling $FAST_MODEL..."
        ollama pull "$FAST_MODEL"
        echo "Models pulled successfully!"
    else
        echo "Required models are available"
    fi
fi

# Create necessary directories
mkdir -p /data/decisions
mkdir -p /data/logs
mkdir -p /data/chroma
mkdir -p /data/manuals

# Phase 6: Ensure agents.yaml exists in persistent config
if [ ! -f /config/agents.yaml ]; then
    echo "Creating default agents.yaml in /config..."
    if [ -f /app/agents.yaml ]; then
        cp /app/agents.yaml /config/agents.yaml
    else
        echo "agents: []" > /config/agents.yaml
    fi
fi

# Link /config/agents.yaml to where the app expects it (or update app to look in /config)
# For now, we update the app to use /config/agents.yaml via environment variable or symlink
rm -f /app/backend/agents.yaml
ln -sf /config/agents.yaml /app/backend/agents.yaml
echo "Linked agents.yaml to persistent storage"

echo "=========================================="
echo "Starting FastAPI Backend"
echo "=========================================="

# Start FastAPI backend
cd /app/backend
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8999 \
    --log-level "${LOG_LEVEL,,}" \
    --no-access-log
