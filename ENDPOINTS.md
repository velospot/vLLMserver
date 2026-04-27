# API Endpoints Reference

## Model Discovery

### List All Models with Specifications
```http
GET /v1/models/detailed
```

Returns all HuggingFace cached models with detailed specs.

**Example:**
```bash
curl http://localhost:8000/v1/models/detailed | jq
```

**Response:**
```json
{
  "object": "list",
  "total": 3,
  "data": [
    {
      "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "object": "model",
      "created": 1704067200,
      "owned_by": "vllmserver",
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

---

## Chat Completions

### Create Chat Completion
```http
POST /v1/chat/completions
X-API-Key: sk-prod-primary
```

**Request:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-prod-primary" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7,
    "max_tokens": 512,
    "stream": false
  }'
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
        "content": "Hello! How can I help you?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

### Streaming Chat
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-prod-primary" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Say hello"}],
    "stream": true
  }'
```

**Response (SSE):**
```
data: {"id":"chatcmpl-xyz...","choices":[{"delta":{"role":"assistant"}}]}

data: {"id":"chatcmpl-xyz...","choices":[{"delta":{"content":"Hello"}}]}

data: {"id":"chatcmpl-xyz...","choices":[{"delta":{"content":"!"}}]}

data: {"id":"chatcmpl-xyz...","choices":[{"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

---

## Embeddings

### Create Embeddings
```http
POST /v1/embeddings
X-API-Key: sk-prod-primary
```

**Request:**
```bash
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-prod-primary" \
  -d '{
    "model": "BAAI/bge-m3",
    "input": ["Hello world", "Another text"]
  }'
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

---

## Rate Limiting

### Get Rate Limit Status
```http
GET /v1/rate-limits
X-API-Key: sk-prod-primary
```

**Request:**
```bash
curl -H "X-API-Key: sk-prod-primary" \
  http://localhost:8000/v1/rate-limits
```

**Response:**
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

**Error (rate limit exceeded):**
```http
HTTP/1.1 429 Too Many Requests

{
  "detail": "Token limit exceeded: 45000 tokens remaining this minute"
}
```

---

## Operations

### List Loaded Models
```http
GET /v1/models
```

Returns only currently loaded models (chat and/or embedding).

**Response:**
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

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "chat_model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "embedding_model": "BAAI/bge-m3"
}
```

### Prometheus Metrics
```http
GET /metrics
```

**Response (excerpt):**
```
# HELP llm_time_to_first_token_seconds Time from request to first generated token
# TYPE llm_time_to_first_token_seconds histogram
llm_time_to_first_token_seconds_bucket{model="Qwen/Qwen2.5-7B-Instruct-AWQ",le="0.05"} 2.0
llm_time_to_first_token_seconds_sum{model="Qwen/Qwen2.5-7B-Instruct-AWQ"} 0.087

# HELP llm_tokens_generated_total Total tokens generated
# TYPE llm_tokens_generated_total counter
llm_tokens_generated_total{model="Qwen/Qwen2.5-7B-Instruct-AWQ"} 12345.0

# HELP llm_requests_in_flight Requests currently being processed
# TYPE llm_requests_in_flight gauge
llm_requests_in_flight{endpoint="chat_completions"} 2.0
```

---

## Authentication

### Optional API Key Header
All endpoints except `/health`, `/docs`, `/v1/models/detailed` support authentication:

```bash
curl -H "X-API-Key: sk-prod-primary" http://localhost:8000/v1/chat/completions ...
```

**Valid keys (edit in `app/auth.py`):**
- `sk-dev-test` — Development tier
- `sk-prod-primary` — Production tier

**No key provided:**
- Allowed but tracked as "anonymous" user
- Subject to shared rate limits
- Recommended for demo/testing only

---

## Error Responses

### 401 Unauthorized (Invalid API Key)
```json
{
  "detail": "Invalid API key"
}
```

### 429 Too Many Requests (Rate Limited)
```json
{
  "detail": "Token limit exceeded: 45000 tokens remaining this minute"
}
```

### 500 Internal Server Error (Generation Failed)
```json
{
  "detail": "CUDA out of memory"
}
```

### 503 Service Unavailable (Model Not Loaded)
```json
{
  "detail": "Chat model not loaded"
}
```

---

## Python Client Examples

### Using OpenAI SDK
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-prod-primary"
)

# Chat
response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct-AWQ",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct-AWQ",
    messages=[{"role": "user", "content": "Tell a story"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")

# Embeddings
embeddings = client.embeddings.create(
    model="BAAI/bge-m3",
    input=["Hello", "World"]
)
for data in embeddings.data:
    print(f"Embedding {data.index}: {len(data.embedding)} dimensions")
```

### Direct HTTP with requests
```python
import requests
import json

headers = {
    "X-API-Key": "sk-prod-primary",
    "Content-Type": "application/json"
}

payload = {
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
}

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers=headers,
    json=payload
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```
