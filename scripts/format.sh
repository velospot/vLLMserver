#!/usr/bin/env bash
# Format code with Black and Ruff
# Usage: ./scripts/format.sh

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
echo "Formatting Code"
echo "=========================================="

# Black formatting
echo ""
echo "🎨 Black Formatter..."
.venv/bin/black app tests main.py
echo "✅ Black formatting complete"

# Ruff import sorting and fixes
echo ""
echo "📦 Ruff (sort imports + autofix)..."
.venv/bin/ruff check app tests --fix --select I,E,W,UP
echo "✅ Ruff formatting complete"

echo ""
echo "=========================================="
echo "✅ All formatting complete!"
echo "=========================================="
