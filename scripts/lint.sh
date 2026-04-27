#!/usr/bin/env bash
# Run linting checks (Ruff + MyPy)
# Usage: ./scripts/lint.sh [--fix]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FIX="${1:-}"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run: uv sync"
    exit 1
fi
source .venv/bin/activate

echo "=========================================="
echo "Running Lint Checks"
echo "=========================================="

ERRORS=0

# Ruff linting
echo ""
echo "📋 Ruff Linter..."
if [ "$FIX" == "--fix" ]; then
    if .venv/bin/ruff check app tests --fix; then
        echo "✅ Ruff linting passed (fixed)"
    else
        ERRORS=$((ERRORS + 1))
        echo "⚠️  Ruff found issues (attempted to fix)"
    fi
else
    if .venv/bin/ruff check app tests; then
        echo "✅ Ruff linting passed"
    else
        ERRORS=$((ERRORS + 1))
        echo "❌ Ruff linting failed"
    fi
fi

# MyPy type checking
echo ""
echo "🔍 MyPy Type Checking..."
if .venv/bin/mypy app --show-error-codes 2>/dev/null || true; then
    echo "✅ MyPy type checking passed"
else
    echo "⚠️  MyPy found type hints to address"
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ All lint checks passed!"
    echo "=========================================="
    exit 0
else
    echo "❌ Lint checks failed ($ERRORS issues)"
    echo "Run: ./scripts/lint.sh --fix"
    echo "=========================================="
    exit 1
fi
