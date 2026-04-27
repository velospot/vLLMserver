#!/usr/bin/env bash
# Test CUDA and vLLM initialization
# Usage: ./scripts/test_cuda.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "CUDA & vLLM Initialization Test"
echo "=========================================="
echo ""

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found"
    echo "Run: ./scripts/setup.sh"
    exit 1
fi
source .venv/bin/activate

# 1. Check CUDA
echo "1️⃣  Checking CUDA..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ nvidia-smi found"
    nvidia-smi --query-gpu=name --format=csv,noheader
else
    echo "⚠️  nvidia-smi not found"
fi
echo ""

# 2. Check PyTorch CUDA
echo "2️⃣  Checking PyTorch CUDA..."
.venv/bin/python3 << 'EOF'
import torch
if torch.cuda.is_available():
    print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
    print(f"   Version: {torch.version.cuda}")
else:
    print("❌ CUDA not available in PyTorch")
EOF
echo ""

# 3. Check vLLM
echo "3️⃣  Checking vLLM..."
.venv/bin/python3 << 'EOF'
try:
    import vllm
    print(f"✅ vLLM installed: v{vllm.__version__}")
except ImportError:
    print("❌ vLLM not installed")
    import sys
    sys.exit(1)
EOF
echo ""

# 4. Test multiprocessing spawn method
echo "4️⃣  Testing multiprocessing spawn method..."
.venv/bin/python3 << 'EOF'
import multiprocessing
import sys

# This is what main.py does
try:
    multiprocessing.set_start_method('spawn', force=True)
    method = multiprocessing.get_start_method()
    if method == 'spawn':
        print(f"✅ Spawn method set: {method}")
    else:
        print(f"⚠️  Method is: {method} (not spawn)")
except RuntimeError as e:
    print(f"⚠️  Could not set spawn: {e}")
    try:
        method = multiprocessing.get_start_method()
        print(f"   Current method: {method}")
    except:
        pass
EOF
echo ""

# 5. Test app initialization
echo "5️⃣  Testing app initialization..."
.venv/bin/python3 << 'EOF'
import sys
from app.platform_detect import MODE, USE_MOCK_VLLM, CUDA_AVAILABLE

print(f"✅ Platform detection:")
print(f"   Mode: {MODE}")
print(f"   Using mock vLLM: {USE_MOCK_VLLM}")
print(f"   CUDA available: {CUDA_AVAILABLE}")
EOF
echo ""

# 6. Test llm_init module
echo "6️⃣  Testing llm_init module..."
.venv/bin/python3 << 'EOF'
from app.llm_init import ensure_spawn_method
try:
    method = ensure_spawn_method()
    print(f"✅ llm_init.ensure_spawn_method() works: {method}")
except Exception as e:
    print(f"❌ Error: {e}")
    import sys
    sys.exit(1)
EOF
echo ""

echo "=========================================="
echo "✅ CUDA initialization test complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  ./scripts/start.sh prod    # Start production server"
echo "  ./scripts/start.sh dev     # Start development server"
echo ""
