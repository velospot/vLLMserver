#!/usr/bin/env bash
# Development workflow helper
# Usage: ./scripts/dev.sh [lint|format|test|check|all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ACTION="${1:-all}"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run: ./scripts/setup.sh"
    exit 1
fi
source .venv/bin/activate

echo "=========================================="
echo "Development Workflow"
echo "=========================================="

case "$ACTION" in
    lint)
        echo "Running linting..."
        "$SCRIPT_DIR/lint.sh"
        ;;

    format)
        echo "Running formatting..."
        "$SCRIPT_DIR/format.sh"
        ;;

    test)
        echo "Running tests..."
        "$SCRIPT_DIR/test.sh" -v
        ;;

    check)
        echo "Running all checks..."
        echo ""
        echo "1️⃣  Formatting..."
        "$SCRIPT_DIR/format.sh"
        echo ""
        echo "2️⃣  Linting..."
        "$SCRIPT_DIR/lint.sh"
        echo ""
        echo "3️⃣  Testing..."
        "$SCRIPT_DIR/test.sh" -v
        echo ""
        echo "=========================================="
        echo "✅ All checks passed!"
        echo "=========================================="
        ;;

    all)
        echo "Running full development workflow..."
        echo ""
        echo "1️⃣  Checking code quality..."
        if "$SCRIPT_DIR/lint.sh"; then
            echo "✅ Linting passed"
        else
            echo "⚠️  Linting issues found"
            echo "Running autofix..."
            "$SCRIPT_DIR/format.sh"
        fi
        echo ""
        echo "2️⃣  Running tests..."
        if "$SCRIPT_DIR/test.sh" -v; then
            echo "✅ Tests passed"
        else
            echo "❌ Tests failed"
            exit 1
        fi
        echo ""
        echo "=========================================="
        echo "✅ All development checks passed!"
        echo "=========================================="
        ;;

    *)
        echo "Usage: $0 [lint|format|test|check|all]"
        echo ""
        echo "  lint   - Run linting checks"
        echo "  format - Format code with Black/Ruff"
        echo "  test   - Run test suite"
        echo "  check  - Run format + lint + test"
        echo "  all    - Run all checks with autofix (default)"
        exit 1
        ;;
esac
