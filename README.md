# vLLM Inference Server

Production-ready FastAPI server for LLM inference using vLLM with OpenAI-compatible endpoints. Supports concurrent requests, streaming responses, and optional text embeddings.

## Features

- **OpenAI-compatible API** — drop-in replacement for OpenAI clients
- **Async concurrency** — vLLM's `AsyncLLMEngine` batches requests intelligently
- **Streaming** — Server-Sent Events (SSE) for real-time token streaming
- **Separate endpoints** — dedicated routes for chat and embeddings
- **Optional embeddings** — load embedding model only if needed (saves VRAM)
- **GPU-optimized** — tensor parallelism, quantization support (AWQ, GPTQ)
- **Headless-ready** — runs on Ubuntu servers with CUDA/ROCm
- **Production-hardened** — API authentication, token-aware rate limiting, observability metrics
- **Model discovery** — scan HF cache and list all available models with specs
- **Metrics & observability** — Prometheus endpoints, TTFT tracking, token counting

## Installation

**Requirements:** Python ≥3.13, CUDA 12.1+ (optional, for GPU support)

### macOS (Development)

```bash
# Verify Python 3.13+
python3 --version

# Clone or navigate to project
cd vllmserver

# Install dependencies using uv
uv sync
```

### Ubuntu (Production with GPU)

```bash
# Verify Python 3.13+
python3 --version

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv

# Install project dependencies with GPU support
uv sync --extra gpu
```

See [PYTHON313_COMPATIBILITY.md](PYTHON313_COMPATIBILITY.md) for detailed compatibility information.

## Quick Start

### Using Scripts (Recommended)

```bash
# First-time setup
./scripts/setup.sh

# Start development server
./scripts/start.sh dev

# In another terminal, check health
curl http://localhost:8000/health
```

Server starts at `http://0.0.0.0:8000`

### Manual Setup

```bash
# Install dependencies
uv sync

# Create .env file
cp .env.example .env

# Customize settings (optional)
nano .env

# Start server
python main.py
```

### Check Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "mode": "development",
  "chat_model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "embedding_model": null,
  "using_mock_vllm": true
}
```

## Production Features

### API Authentication

All endpoints except `/health`, `/docs`, and `/v1/models/detailed` support optional API key authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: sk-prod-primary" http://localhost:8000/v1/chat/completions ...
```

Default keys (configure in `app/auth.py` for production):
- `sk-dev-test` — development tier
- `sk-prod-primary` — production tier

### Token-Aware Rate Limiting

Instead of simple request counting, the server tracks three metrics:
- **RPM** — Requests per minute
- **TPM** — Tokens per minute (input + output)
- **TPD** — Tokens per day

Configuration:
```python
# app/rate_limit.py
limiter = TokenRateLimiter(
    rpm_limit=60,        # 60 requests per minute
    tpm_limit=100000,    # 100k tokens per minute
    tpd_limit=10000000,  # 10M tokens per day
)
```

Check current usage:
```bash
curl -H "X-API-Key: sk-prod-primary" http://localhost:8000/v1/rate-limits
```

Response:
```json
{
  "requests_this_minute": 5,
  "tokens_this_minute": 2345,
  "tokens_today": 89234,
  "rpm_limit": 60,
  "tpm_limit": 100000,
  "tpd_limit": 10000000
}
```

### Observability & Metrics

Prometheus metrics available at `/metrics`:

**Key LLM metrics:**
- `llm_time_to_first_token_seconds` — TTFT (perceived latency)
- `llm_time_per_token_seconds` — token generation throughput
- `llm_tokens_generated_total` — total tokens produced
- `llm_requests_in_flight` — concurrent requests
- `llm_queue_depth` — requests waiting for GPU
- `llm_request_duration_seconds` — total request time

Example Prometheus scrape config:
```yaml
scrape_configs:
  - job_name: 'vllm'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

## Configuration

Environment files are loaded automatically based on the startup mode. Use the provided helper scripts:

```bash
# First-time setup (creates .env.dev and .env.prod)
./scripts/setup.sh

# Start development server (loads .env.dev)
./scripts/start.sh dev

# Start production server (loads .env.prod)
./scripts/start.sh prod
```

Or manually set environment variables:

```bash
export CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
export CHAT_GPU_MEM_UTIL=0.9
export CHAT_MAX_NUM_SEQS=256
python main.py
```

### Environment Files

- **`.env.dev`** — Development settings (macOS compatible, smaller batch size, debug logging)
- **`.env.prod`** — Production settings (Linux+GPU, optimized batch size, strict rate limits)
- **`.env.example`** — Template for creating custom configurations

### Chat Model

| Env Var | Default | Description |
|---|---|---|
| `CHAT_MODEL` | `Qwen/Qwen2.5-7B-Instruct-AWQ` | HF model ID or local path |
| `CHAT_GPU_MEM_UTIL` | `0.7` | Fraction of GPU VRAM (0.0–1.0) |
| `CHAT_MAX_MODEL_LEN` | `4096` | Context window in tokens |
| `CHAT_MAX_NUM_SEQS` | `256` | Max concurrent sequences in batch |
| `CHAT_TENSOR_PARALLEL` | `1` | Number of GPUs for tensor parallelism |
| `CHAT_DTYPE` | `auto` | `float16`, `bfloat16`, or `auto` |
| `CHAT_QUANTIZATION` | (auto-detect) | `awq`, `gptq`, etc. (usually auto-detected) |

### Embedding Model (optional)

| Env Var | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | (disabled) | HF model ID (e.g., `BAAI/bge-m3`) |
| `EMBEDDING_GPU_MEM_UTIL` | `0.2` | Fraction of GPU VRAM |
| `EMBEDDING_MAX_MODEL_LEN` | `512` | Max input length |
| `EMBEDDING_TENSOR_PARALLEL` | `1` | Number of GPUs |

### Server

| Env Var | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Listen port |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warning`, `error` |

## API Endpoints

### Model Discovery

#### List detailed model specs

`GET /v1/models/detailed`

Returns all cached HuggingFace models with detailed specifications:

```bash
curl http://localhost:8000/v1/models/detailed
```

Response (excerpt):
```json
{
  "object": "list",
  "total": 3,
  "data": [
    {
      "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "architecture": "QwenForCausalLM",
      "parameters": 7000000000,
      "size_gb": 5.2,
      "quantization": "AWQ",
      "capabilities": {
        "context_length": 4096,
        "max_completion_tokens": 2048,
        "supports_streaming": true,
        "supports_system_prompt": true
      },
      "limits": {
        "rpm": 60,
        "tpm": 100000,
        "tpd": 10000000,
        "max_batch_size": 256
      },
      "tags": ["awq", "instruction-tuned"]
    }
  ]
}
```

**Note:** Lists both loaded models (currently running) and available models (in HF cache but not loaded). Use `EMBEDDING_MODEL` env var to load embedding models.

### Chat Completions

`POST /v1/chat/completions`

**Request:**
```json
{
  "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"}
  ],
  "temperature": 0.7,
  "max_tokens": 512,
  "top_p": 0.9,
  "stream": false
}
```

**Response (non-streaming):**
```json
{
  "id": "chatcmpl-abc123...",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "2 + 2 = 4"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 8,
    "total_tokens": 50
  }
}
```

**Streaming example:**

With `"stream": true`, responses arrive as SSE chunks:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Say hello"}],
    "stream": true
  }'
```

Output:
```
data: {"id":"chatcmpl-xyz...","object":"chat.completion.chunk","created":1704067200,"model":"Qwen/Qwen2.5-7B-Instruct-AWQ","choices":[{"index":0,"delta":{"role":"assistant"}}]}

data: {"id":"chatcmpl-xyz...","object":"chat.completion.chunk","created":1704067200,"model":"Qwen/Qwen2.5-7B-Instruct-AWQ","choices":[{"index":0,"delta":{"content":"Hello"}}]}

data: {"id":"chatcmpl-xyz...","object":"chat.completion.chunk","created":1704067200,"model":"Qwen/Qwen2.5-7B-Instruct-AWQ","choices":[{"index":0,"delta":{"content":"!"}}]}

data: {"id":"chatcmpl-xyz...","object":"chat.completion.chunk","created":1704067200,"model":"Qwen/Qwen2.5-7B-Instruct-AWQ","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Embeddings

`POST /v1/embeddings`

**Request:**
```json
{
  "model": "BAAI/bge-m3",
  "input": ["Hello world", "Another text"]
}
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.123, -0.456, 0.789, ...]
    },
    {
      "object": "embedding",
      "index": 1,
      "embedding": [0.234, -0.567, 0.890, ...]
    }
  ],
  "model": "BAAI/bge-m3",
  "usage": {
    "prompt_tokens": 8,
    "total_tokens": 8
  }
}
```

### List Models

`GET /v1/models`

Returns available models:
```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "object": "model",
      "created": 1704067200,
      "owned_by": "vllmserver"
    },
    {
      "id": "BAAI/bge-m3",
      "object": "model",
      "created": 1704067200,
      "owned_by": "vllmserver"
    }
  ]
}
```

### Prometheus Metrics

`GET /metrics`

Exposes all metrics in Prometheus text format:

```bash
curl http://localhost:8000/metrics | grep llm_
```

Example output:
```
# HELP llm_time_to_first_token_seconds Time from request to first generated token
# TYPE llm_time_to_first_token_seconds histogram
llm_time_to_first_token_seconds_bucket{model="Qwen/Qwen2.5-7B-Instruct-AWQ",le="0.01"} 0.0
llm_time_to_first_token_seconds_bucket{model="Qwen/Qwen2.5-7B-Instruct-AWQ",le="0.1"} 4.0

# HELP llm_tokens_generated_total Total tokens generated
# TYPE llm_tokens_generated_total counter
llm_tokens_generated_total{model="Qwen/Qwen2.5-7B-Instruct-AWQ"} 12345.0
```

### Interactive Docs

Open browser to `http://localhost:8000/docs` for Swagger UI with live API testing.

## Python Client Example

Using `openai` library (compatible):

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")

# Chat completion
response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct-AWQ",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.7,
    max_tokens=512
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct-AWQ",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

# Embeddings
embeddings = client.embeddings.create(
    model="BAAI/bge-m3",
    input=["Hello world", "Test"]
)
for data in embeddings.data:
    print(f"Index {data.index}: {len(data.embedding)} dims")
```

## Deployment on Ubuntu Server

### 1. System setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.13+
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install CUDA (if not present)
# Follow: https://developer.nvidia.com/cuda-downloads
# Verify: nvidia-smi
```

### 2. Clone and setup

```bash
# Clone repository
git clone <your-repo> /home/vllm/vllmserver
cd /home/vllm/vllmserver

# Install dependencies with GPU support
uv sync --extra gpu

# Customize production settings
nano .env.prod
```

### 3. Create systemd service

Create `/etc/systemd/system/vllm-server.service`:

```ini
[Unit]
Description=vLLM Inference Server
After=network.target

[Service]
Type=simple
User=vllm
WorkingDirectory=/home/vllm/vllmserver
Environment="PATH=/home/vllm/vllmserver/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=/home/vllm/vllmserver/scripts/start.sh prod
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

The `start.sh prod` script will:
- Load settings from `.env.prod`
- Verify vLLM is installed
- Start the server with optimized production configuration

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vllm-server
sudo systemctl start vllm-server
sudo systemctl status vllm-server

# View logs
sudo journalctl -u vllm-server -f
```

### 3. Reverse proxy (Nginx)

```nginx
upstream vllm {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://vllm;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;  # Important for streaming
        proxy_request_buffering off;
    }
}
```

Reload: `sudo systemctl reload nginx`

## Performance Tuning

### High concurrency (1000+ req/s)

```bash
# Increase batch size and context
CHAT_MAX_NUM_SEQS=512
CHAT_MAX_MODEL_LEN=2048
CHAT_GPU_MEM_UTIL=0.9

# Use tensor parallelism across GPUs
CHAT_TENSOR_PARALLEL=4
```

### Low latency (P99 < 500ms)

```bash
# Smaller batch and quantization
CHAT_MAX_NUM_SEQS=32
CHAT_GPU_MEM_UTIL=0.6
CHAT_QUANTIZATION=awq

# Disable embedding to reserve GPU
# (don't set EMBEDDING_MODEL)
```

### Memory-constrained (< 16GB VRAM)

```bash
# Smaller model
CHAT_MODEL=Qwen/Qwen2.5-1.5B-Instruct

# Aggressive quantization
CHAT_QUANTIZATION=awq
CHAT_GPU_MEM_UTIL=0.5

# Disable embeddings
```

## Production Best Practices (Premai 2026)

This server implements key patterns from the Premai guide on production LLM serving:

### 1. Token-Aware Rate Limiting
Unlike HTTP request counting, this tracks **token consumption** to prevent GPU monopolization:
```python
# One user: 50-word prompt = 1 request
# Another user: 10,000-word document = 1 request (but 200x more tokens)
# This limits based on tokens, not requests
```

### 2. Authentication Before Rate Limiting
API keys validated at request entry, before any processing. Prevents wasted GPU cycles on invalid requests.

### 3. Observability Metrics
Track **LLM-specific** metrics, not generic HTTP metrics:
- **TTFT** (time to first token) — how long before users see output
- **Tokens/sec** — throughput indicator
- **Queue depth** — capacity planning
- **KV cache usage** — memory pressure indicator

### 4. Streaming with SSE
Server-Sent Events maintain persistent connections with optional heartbeats. Perceived latency improves when users see first token quickly.

### 5. Async-Only Architecture
All endpoints use FastAPI async + vLLM's `AsyncLLMEngine`. Synchronous calls block the event loop and prevent concurrent handling.

### 6. Model Discovery
Scan HuggingFace cache to dynamically list available models with their specifications. Enables runtime model switching without redeployment.

## Architecture

- **AsyncLLMEngine**: vLLM's async batching engine handles all concurrency
- **Pydantic models**: Input validation + OpenAI schema compatibility
- **Separate engines**: Chat and embedding models run in independent vLLM instances
- **app.state**: FastAPI lifespan context stores model engines
- **Token-aware limiter**: In-memory (production: use Redis for distributed systems)
- **Metrics**: Prometheus integration for dashboarding (Grafana, Datadog, etc.)
- **Model cache scanner**: HuggingFace cache discovery for runtime flexibility

## Monitoring

Check logs:
```bash
# Systemd
sudo journalctl -u vllm-server -f

# Or direct run
python main.py 2>&1 | grep -i error
```

Health endpoint (no logs):
```bash
curl http://localhost:8000/health
```

## Troubleshooting

| Issue | Solution |
|---|---|
| CUDA out of memory | Lower `CHAT_GPU_MEM_UTIL`, disable embedding, use smaller model |
| High latency | Reduce `CHAT_MAX_NUM_SEQS`, increase `CHAT_GPU_MEM_UTIL` |
| 503 errors | Models still loading; wait a minute or check logs |
| Streaming stops | Check proxy buffering settings (use `proxy_buffering off`) |

## License

Same as vLLM project (Apache 2.0).
