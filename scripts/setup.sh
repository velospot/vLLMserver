#!/usr/bin/env bash
# Setup development environment
# Usage: ./scripts/setup.sh [--gpu]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INSTALL_GPU="${1:-}"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Setting Up Development Environment"
echo "=========================================="

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
if [ -z "$PYTHON_VERSION" ]; then
    echo "❌ python3 not found"
    echo "Install Python 3.13+: https://www.python.org/downloads/"
    exit 1
fi

MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 13 ]); then
    echo "❌ Python 3.13+ required, found: $PYTHON_VERSION"
    echo "Install from: https://www.python.org/downloads/"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION detected"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "Install from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
if [ "$INSTALL_GPU" == "--gpu" ]; then
    echo "   (with GPU support)"
    uv sync --extra gpu
else
    echo "   (development/testing mode)"
    uv sync
fi

# Make scripts executable
echo ""
echo "🔧 Making scripts executable..."
chmod +x "$SCRIPT_DIR"/*.sh

# Create environment files if they don't exist
echo ""
echo "⚙️  Creating environment configuration..."
if [ ! -f .env.dev ]; then
    cp .env.example .env.dev
    echo "✅ Created .env.dev"
else
    echo "✅ .env.dev already exists"
fi
if [ ! -f .env.prod ]; then
    cp .env.example .env.prod
    echo "✅ Created .env.prod"
else
    echo "✅ .env.prod already exists"
fi

# Verify installation
echo ""
echo "✅ Verifying installation..."
source .venv/bin/activate
.venv/bin/python -c "from app.main import app; print('✅ App imports successfully')"

echo ""
echo "=========================================="
echo "✅ Development environment ready!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start dev server:  ./scripts/start.sh dev"
echo "  2. Run tests:         ./scripts/test.sh"
echo "  3. Format code:       ./scripts/format.sh"
echo "  4. Lint code:         ./scripts/lint.sh"
echo ""
