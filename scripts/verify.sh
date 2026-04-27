#!/usr/bin/env bash
# Verify Python 3.13 setup and dependencies
# Usage: ./scripts/verify.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Verification: Python 3.13 Setup"
echo "=========================================="
echo ""

# 1. Check Python version
echo "1️⃣  Checking Python version..."
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null)
MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)' 2>/dev/null)
MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null)

if [ -z "$PYTHON_VERSION" ]; then
    echo "❌ Python 3 not found"
    exit 1
fi

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 13 ]); then
    echo "❌ Python 3.13+ required, found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION"
echo ""

# 2. Check virtual environment
echo "2️⃣  Checking virtual environment..."
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found at .venv"
    echo "   Run: ./scripts/setup.sh"
    exit 1
fi
echo "✅ Virtual environment exists"
echo ""

# 3. Activate venv and check installed packages
echo "3️⃣  Checking installed dependencies..."
source .venv/bin/activate

# Core dependencies
DEPS_OK=true
for dep in fastapi uvicorn transformers huggingface_hub prometheus_client pydantic jinja2; do
    if python3 -c "import ${dep//[_-]/__}" 2>/dev/null; then
        echo "✅ $dep"
    else
        echo "⚠️  $dep (not installed)"
        DEPS_OK=false
    fi
done
echo ""

# 4. Check dev dependencies
echo "4️⃣  Checking development dependencies..."
DEV_DEPS_OK=true
for dep in pytest pytest_asyncio httpx ruff black mypy; do
    if python3 -c "import ${dep//[_-]/__}" 2>/dev/null; then
        echo "✅ $dep"
    else
        echo "⚠️  $dep (not installed for dev)"
        DEV_DEPS_OK=false
    fi
done
echo ""

# 5. Check configuration
echo "5️⃣  Checking configuration files..."
if grep -q 'requires-python = ">=3.13"' pyproject.toml; then
    echo "✅ pyproject.toml requires Python >=3.13"
else
    echo "❌ pyproject.toml doesn't require Python 3.13"
    exit 1
fi

if grep -q 'target-version = "py313"' pyproject.toml; then
    echo "✅ Ruff configured for Python 3.13"
else
    echo "⚠️  Ruff not configured for Python 3.13"
fi

if grep -q 'python_version = "3.13"' pyproject.toml; then
    echo "✅ MyPy configured for Python 3.13"
else
    echo "⚠️  MyPy not configured for Python 3.13"
fi
echo ""

# 6. Check platform detection
echo "6️⃣  Checking platform detection..."
if python3 -c "from app.platform_detect import MODE, USE_MOCK_VLLM; print(f'Mode: {MODE}, Mock vLLM: {USE_MOCK_VLLM}')" 2>/dev/null; then
    echo "✅ Platform detection works"
else
    echo "⚠️  Platform detection issue (app may not be importable yet)"
fi
echo ""

# Summary
echo "=========================================="
if [ "$DEPS_OK" = true ]; then
    echo "✅ Core dependencies verified"
else
    echo "⚠️  Some core dependencies missing (run: uv sync)"
fi

if [ "$DEV_DEPS_OK" = true ]; then
    echo "✅ Dev dependencies verified"
else
    echo "⚠️  Some dev dependencies missing (run: uv sync)"
fi

echo "✅ Python 3.13 setup verified"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  ./scripts/start.sh dev    # Start development server"
echo "  ./scripts/dev.sh check    # Run quality checks"
echo ""
