# CUDA Production Setup & Troubleshooting

## Issue: RuntimeError - Cannot re-initialize CUDA in forked subprocess

### Error Message
```
RuntimeError: Cannot re-initialize CUDA in forked subprocess. 
To use CUDA with multiprocessing, you must use the 'spawn' start method
```

### Root Cause
When vLLM initializes CUDA in the parent process and then uvicorn tries to fork worker processes, the forked processes inherit CUDA state but cannot reinitialize it. This causes a crash.

### Solution Implemented ✅

**1. Multiprocessing Start Method (main.py)**
```python
if not USE_MOCK_VLLM:
    multiprocessing.set_start_method('spawn', force=True)
```

**2. Single Worker Configuration**
```python
uvicorn.run(
    "app.main:app",
    workers=1,  # vLLM manages its own async concurrency
    ...
)
```

**3. Enhanced Error Messages**
When CUDA initialization fails, the server now provides diagnostic guidance.

---

## Production Deployment Checklist

### System Requirements
- [ ] Linux (Ubuntu 20.04+)
- [ ] NVIDIA GPU (RTX 3090, A100, H100, etc.)
- [ ] CUDA 12.1+ installed
- [ ] cuDNN 8.x installed
- [ ] Python 3.13+
- [ ] PyTorch with CUDA support

### Verification Steps

#### 1. Check CUDA Installation
```bash
# Verify CUDA is available
nvidia-smi

# Should output GPU info:
# NVIDIA-SMI 535.0+ CUDA Capability: 12.1+
```

#### 2. Verify Python & vLLM
```bash
# Check Python version
python3 --version  # Must be 3.13+

# Verify vLLM installation
python3 -c "import vllm; print(vllm.__version__)"

# Test CUDA from Python
python3 -c "import torch; print(torch.cuda.is_available())"
# Should print: True
```

#### 3. Test vLLM Directly
```bash
python3 << 'EOF'
from vllm import LLM

# Initialize real vLLM (will load model)
llm = LLM("Qwen/Qwen2.5-1.5B-Instruct", gpu_memory_utilization=0.5)
print("✅ vLLM initialized successfully")
EOF
```

#### 4. Verify Multiprocessing Setup
```bash
python3 << 'EOF'
import multiprocessing
import sys

# Check current method
try:
    method = multiprocessing.get_start_method()
    print(f"Multiprocessing start method: {method}")
except:
    method = "Not set"

# For CUDA safety, should be 'spawn'
if method == 'spawn':
    print("✅ Correct: Using 'spawn' start method (CUDA safe)")
else:
    print(f"⚠️  Current method: {method} (may cause CUDA issues)")
EOF
```

### Configuration (from .env.prod)

```bash
# Chat Model Settings
CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
CHAT_GPU_MEM_UTIL=0.9              # High GPU utilization
CHAT_MAX_MODEL_LEN=4096            # Full context window
CHAT_MAX_NUM_SEQS=256              # Higher batch for throughput
CHAT_TENSOR_PARALLEL=1             # Increase for multi-GPU
CHAT_DTYPE=bfloat16                # Mixed precision for speed

# Embedding Model (optional)
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_GPU_MEM_UTIL=0.1

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
```

### Start Server

**Option 1: Using scripts (recommended)**
```bash
./scripts/setup.sh --gpu
./scripts/start.sh prod
```

**Option 2: Manual**
```bash
export CUDA_VISIBLE_DEVICES=0  # Specify GPU(s)
python3 main.py
```

### Monitoring

```bash
# Check server is running
curl http://localhost:8000/health

# Monitor GPU usage
watch -n 1 nvidia-smi

# Check logs
tail -f /var/log/vllm-server.log
```

---

## Common Issues & Solutions

### Issue 1: ModuleNotFoundError: No module named 'vllm'

**Solution:**
```bash
# Install vLLM with GPU support
pip install "vllm>=0.19.1"

# Or with uv
uv sync --extra gpu
```

### Issue 2: CUDA out of memory

**Solution:**
```bash
# Lower GPU memory utilization
export CHAT_GPU_MEM_UTIL=0.7  # From 0.9
export EMBEDDING_GPU_MEM_UTIL=0.05  # From 0.1

# Or reduce batch size
export CHAT_MAX_NUM_SEQS=128  # From 256

# Or use smaller model
export CHAT_MODEL=Qwen/Qwen2.5-1.5B-Instruct
```

### Issue 3: torch.cuda.OutOfMemoryError during model load

**Solution:**
```bash
# Ensure only using one GPU
export CUDA_VISIBLE_DEVICES=0

# Clear GPU cache
nvidia-smi | grep python | awk '{print $5}' | xargs kill -9  # Kill zombie processes

# Restart server
```

### Issue 4: ImportError with torch/transformers

**Solution:**
```bash
# Reinstall with correct CUDA version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify PyTorch CUDA
python3 -c "import torch; print(torch.version.cuda)"
```

### Issue 5: "Cannot find model" errors

**Solution:**
```bash
# Pre-download model to HuggingFace cache
python3 << 'EOF'
from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "Qwen/Qwen2.5-7B-Instruct-AWQ"
print(f"Downloading {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
print("✅ Model cached locally")
EOF
```

---

## Systemd Service Setup

### Create service file: `/etc/systemd/system/vllm-server.service`

```ini
[Unit]
Description=vLLM Inference Server
After=network.target
Wants=nvidia-smi.service

[Service]
Type=simple
User=vllm
Group=vllm
WorkingDirectory=/home/vllm/vllmserver

# CUDA Environment
Environment="PATH=/home/vllm/vllmserver/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH"

# Load .env.prod
EnvironmentFile=%d/vllm-server.env

ExecStart=/home/vllm/vllmserver/scripts/start.sh prod

# Auto-restart on failure
Restart=on-failure
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vllm-server

[Install]
WantedBy=multi-user.target
```

### Service environment file: `/etc/systemd/system/vllm-server.env`

```bash
CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
CHAT_GPU_MEM_UTIL=0.9
CHAT_MAX_NUM_SEQS=256
LOG_LEVEL=info
```

### Enable and start service

```bash
# Create vllm user
sudo useradd -m -s /bin/bash vllm

# Set permissions
sudo chown -R vllm:vllm /home/vllm/vllmserver

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable vllm-server
sudo systemctl start vllm-server

# Check status
sudo systemctl status vllm-server
sudo journalctl -u vllm-server -f
```

---

## Docker Production Deployment

### Dockerfile

```dockerfile
FROM nvidia/cuda:12.1-cudnn8-devel-ubuntu22.04

# Install Python 3.13
RUN apt-get update && apt-get install -y \
    python3.13 python3.13-venv python3.13-dev \
    build-essential git curl

WORKDIR /app
COPY . .

# Setup Python environment
RUN python3.13 -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install uv
RUN uv sync --extra gpu

# Load environment and run
ENV CUDA_VISIBLE_DEVICES=0
EXPOSE 8000

CMD ["python3.13", "main.py"]
```

### Build and run

```bash
# Build
docker build -t vllm-server:latest .

# Run with GPU support
docker run --gpus all \
    -p 8000:8000 \
    -e CUDA_VISIBLE_DEVICES=0 \
    -e CHAT_GPU_MEM_UTIL=0.9 \
    vllm-server:latest
```

---

## Performance Tuning

### For High Throughput (batch processing)
```bash
CHAT_MAX_NUM_SEQS=512
CHAT_GPU_MEM_UTIL=0.95
CHAT_TENSOR_PARALLEL=2  # For 2-GPU setup
```

### For Low Latency (real-time inference)
```bash
CHAT_MAX_NUM_SEQS=32
CHAT_GPU_MEM_UTIL=0.6
CHAT_MAX_MODEL_LEN=2048  # Smaller context
```

### For Multiple GPUs
```bash
CHAT_TENSOR_PARALLEL=2  # 2 GPUs
CHAT_TENSOR_PARALLEL=4  # 4 GPUs
```

---

## Monitoring & Alerts

### Prometheus Metrics
```bash
curl http://localhost:8000/metrics | grep llm_
```

### Key metrics to monitor
- `llm_time_to_first_token_seconds` — Latency
- `llm_tokens_generated_total` — Throughput
- `llm_requests_in_flight` — Concurrency
- `llm_queue_depth` — Backlog

### Grafana Dashboard
Import example dashboards from [Grafana Community](https://grafana.com/grafana/dashboards/).

---

## Testing Production Setup

### Basic health check
```bash
curl -s http://localhost:8000/health | jq
```

### Load test
```bash
# Install wrk if needed
brew install wrk  # macOS
apt-get install wrk  # Ubuntu

# Run load test
wrk -t4 -c100 -d30s \
    -s scripts/load_test.lua \
    http://localhost:8000/v1/chat/completions
```

### Inference test
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100
    }' | jq
```

---

## Rollback & Recovery

### If server fails to start
```bash
# Check logs
journalctl -u vllm-server -n 50

# Reduce GPU memory
export CHAT_GPU_MEM_UTIL=0.5

# Clear cache
rm -rf ~/.cache/huggingface

# Restart
systemctl restart vllm-server
```

### Manual recovery
```bash
# Kill any zombie processes
pkill -f vllm
pkill -f python

# Clear GPU memory
nvidia-smi --query-compute-apps=pid --format=csv,noheader | xargs kill -9

# Restart
./scripts/start.sh prod
```

---

## References

- [vLLM Documentation](https://docs.vllm.ai/)
- [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__DRIVER.html)
- [PyTorch CUDA Setup](https://pytorch.org/get-started/locally/)
- [FastAPI Production Deployment](https://fastapi.tiangolo.com/deployment/)
