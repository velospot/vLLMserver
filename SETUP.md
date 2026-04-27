# Setup Guide: macOS Development vs Linux Production

This project uses **conditional imports** to intelligently select between real vLLM (GPU) and mock vLLM (testing).

## Architecture

```
┌─────────────────────────────────────┐
│  Platform Detection (platform_detect.py)
│  • Detects: macOS, Linux, GPU/CUDA
│  • Sets: MODE (production/development)
│  • Sets: USE_MOCK_VLLM (True/False)
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
   macOS             Linux+GPU
   (Fallback)        (Production)
      │                 │
      └────────┬────────┘
               │
      ┌────────▼──────────┐
      │ vllm_imports.py
      │ Conditional Import
      └────────┬──────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
  mock_vllm.py      real vllm
  (Testing)         (GPU)
```

## Development Setup (macOS)

### 1. Install Dependencies

```bash
cd vllmserver
uv sync
```

This installs:
- ✅ FastAPI, uvicorn, transformers, etc. (cross-platform)
- ❌ vLLM, CUDA libraries (GPU-specific, skipped on macOS)
- ✅ pytest, httpx (dev/testing)

### 2. What Gets Used on macOS

- **vLLM Implementation:** Mock (pure Python, no GPU)
- **Mode:** `development`
- **CUDA Available:** `False`
- **API Endpoints:** Fully functional (mock models return dummy data)

### 3. Verify Setup

```bash
# Check platform detection
python -c "from app.platform_detect import *; print(f'Mode: {MODE}, Using mock: {USE_MOCK_VLLM}')"

# Output: Mode: development, Using mock: True

# Start server (mock models)
python main.py

# In another terminal:
curl http://localhost:8000/system
```

Response (macOS):
```json
{
  "platform": "Darwin",
  "mode": "development",
  "cuda_available": false,
  "using_mock_vllm": true,
  "chat_model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "embedding_model": null
}
```

### 4. Run Tests

```bash
# Install dev dependencies (if not already)
uv sync --extra dev

# Run all tests
python -m pytest tests/ -v

# Or specific test file
python -m pytest tests/test_platform_detection.py -v
```

## Production Setup (Linux + GPU)

### 1. System Requirements

```
OS: Ubuntu 20.04+ or similar Linux
GPU: NVIDIA GPU (RTX 3090, A100, etc.)
CUDA: 12.1+ installed
Python: 3.10-3.12
```

### 2. Install Dependencies with GPU Support

```bash
cd vllmserver

# Install vLLM with GPU support
uv sync --extra gpu

# Or manually
pip install vllm>=0.19.1 torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. What Gets Used on Linux+GPU

- **vLLM Implementation:** Real (compiled with CUDA)
- **Mode:** `production`
- **CUDA Available:** `True`
- **API Endpoints:** Full performance with real models

### 4. Verify Setup

```bash
# Check platform detection
python -c "from app.platform_detect import *; print(f'Mode: {MODE}, CUDA: {CUDA_AVAILABLE}, Using mock: {USE_MOCK_VLLM}')"

# Output: Mode: production, CUDA: True, Using mock: False

# Start server
python main.py

# Check status
curl http://localhost:8000/system
```

Response (Linux+GPU):
```json
{
  "platform": "Linux",
  "mode": "production",
  "cuda_available": true,
  "using_mock_vllm": false,
  "chat_model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "embedding_model": "BAAI/bge-m3"
}
```

### 5. Performance Tuning

Once running with real GPU:

```bash
# Increase GPU utilization
export CHAT_GPU_MEM_UTIL=0.9
export CHAT_MAX_NUM_SEQS=512

# Add embedding model
export EMBEDDING_MODEL=BAAI/bge-m3
export EMBEDDING_GPU_MEM_UTIL=0.8

python main.py
```

## Import Flow

When you import vLLM-related classes:

```python
# In app/services/llm.py
from app.vllm_imports import AsyncEngineArgs, AsyncLLMEngine, SamplingParams

# This resolves as:
# 1. app/vllm_imports.py checks USE_MOCK_VLLM
# 2. If True (macOS): imports from app/mock_vllm.py
# 3. If False (Linux+GPU): imports from real vllm package
```

No try/except blocks needed — the correct implementation is selected at import time.

## File Organization

```
app/
├── platform_detect.py      ← Core detection logic
├── vllm_imports.py         ← Conditional imports (uses platform_detect)
├── mock_vllm.py            ← Mock implementation (macOS/testing)
├── services/
│   ├── llm.py              ← Uses vllm_imports
│   └── embedding.py        ← Uses vllm_imports
└── main.py                 ← Logs platform/mode at startup
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'vllm'"

**On macOS (expected):**
- You're in development mode
- Mock vLLM will be used automatically
- No action needed

**On Linux (unexpected):**
- Run: `pip install vllm`
- Or: `uv sync --extra gpu`

### Server starts but models are slow/stubby

**Check mode:**
```bash
curl http://localhost:8000/system
```

If `using_mock_vllm: true` on Linux, real vLLM isn't installed. Run:
```bash
pip install vllm[cuda12]
# or
uv sync --extra gpu
```

Then restart the server.

### CUDA is available but using mock vLLM

**Cause:** vLLM package not installed (even though CUDA is available)

**Fix:**
```bash
pip install vllm
# Restart server
```

### Different behavior on macOS vs Linux

Expected! 

- **macOS (mock):** Instant responses, 768-dim embeddings, dummy data
- **Linux (real):** Real model inference, actual embeddings, latency

For consistent testing, use the same environment (or Docker) for both.

## CI/CD Considerations

### GitHub Actions Example

```yaml
name: Test

on: [push]

jobs:
  test-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install uv && uv sync
      - run: python -m pytest tests/ -v
      # Uses mock vLLM automatically

  test-linux-gpu:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install uv && uv sync --extra gpu
      - run: python -m pytest tests/ -v
      # Uses real vLLM with CUDA
```

## Docker

### Development Image (small, fast, no GPU)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["python", "main.py"]
# Uses mock vLLM
```

### Production Image (large, with GPU support)

```dockerfile
FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3.11 python3-pip
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --extra gpu
CMD ["python", "main.py"]
# Uses real vLLM with GPU
```

## Summary

| Aspect | macOS (Development) | Linux+GPU (Production) |
|--------|---|---|
| **vLLM Type** | Mock (pure Python) | Real (CUDA-compiled) |
| **Setup** | `uv sync` | `uv sync --extra gpu` |
| **Mode** | `development` | `production` |
| **Latency** | Instant | Real model latency |
| **GPU Usage** | None (CPU-only) | Full GPU utilization |
| **Use Case** | Testing, development | Live inference |
| **CUDA Required** | No | Yes (12.1+) |
