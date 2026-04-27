#!/usr/bin/env bash
# Start vLLM Inference Server
# Usage: ./scripts/start.sh [dev|prod|test]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODE="${1:-dev}"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "vLLM Inference Server Startup"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found"
    echo "Run: uv sync"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

case "$MODE" in
    dev|development)
        echo "Starting in DEVELOPMENT mode (macOS/Mock vLLM)"
        if [ ! -f .env.dev ]; then
            echo "❌ .env.dev not found"
            echo "Create it with: cp .env.example .env.dev"
            exit 1
        fi
        set -a
        source .env.dev
        set +a
        .venv/bin/python main.py
        ;;

    prod|production)
        echo "Starting in PRODUCTION mode (Linux/Real vLLM with GPU)"
        if [ ! -f .env.prod ]; then
            echo "❌ .env.prod not found"
            echo "Create it with: cp .env.example .env.prod"
            exit 1
        fi
        if ! .venv/bin/python -c "import vllm" 2>/dev/null; then
            echo "❌ vLLM not installed"
            echo "Install with: uv sync --extra gpu"
            exit 1
        fi
        set -a
        source .env.prod
        set +a
        .venv/bin/python main.py
        ;;

    test)
        echo "Starting in TEST mode (Mock vLLM, Debug logging)"
        if [ ! -f .env.dev ]; then
            echo "❌ .env.dev not found"
            echo "Create it with: cp .env.example .env.dev"
            exit 1
        fi
        set -a
        source .env.dev
        set +a
        export PORT=8001
        timeout 10 .venv/bin/python main.py || true
        ;;

    *)
        echo "Usage: $0 [dev|prod|test]"
        echo ""
        echo "  dev   - Development mode (default, loads .env.dev)"
        echo "  prod  - Production mode (loads .env.prod)"
        echo "  test  - Test mode (loads .env.dev, 10 second timeout)"
        exit 1
        ;;
esac
