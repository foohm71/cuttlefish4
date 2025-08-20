#!/bin/bash
# Render.com startup script for Cuttlefish Multi-Agent RAG API

echo "🚀 Starting Cuttlefish deployment on Render.com..."

# Set environment variables for production
export PYTHONPATH="/opt/render/project/src"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"

# Debug environment info
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Host: $HOST"
echo "Port: $PORT"

# Check critical environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY not set"
fi

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "⚠️  WARNING: GOOGLE_CLOUD_PROJECT not set (LogSearch will not work)"
fi

if [ -z "$TAVILY_API_KEY" ]; then
    echo "⚠️  WARNING: TAVILY_API_KEY not set (WebSearch will not work)"
fi

# Start the FastAPI application
echo "🌟 Launching FastAPI server..."
exec python -m app.api.main