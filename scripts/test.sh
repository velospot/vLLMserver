#!/usr/bin/env bash
# Run tests with pytest
# Usage: ./scripts/test.sh [tests/file.py] [-v|--verbose] [-k PATTERN]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run: uv sync"
    exit 1
fi
source .venv/bin/activate

echo "=========================================="
echo "Running Tests"
echo "=========================================="

# Run pytest with arguments
.venv/bin/pytest \
    tests/ \
    --tb=short \
    --strict-markers \
    --asyncio-mode=auto \
    "$@"

echo ""
echo "=========================================="
echo "✅ Tests complete"
echo "=========================================="
