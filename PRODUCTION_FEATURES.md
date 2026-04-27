# Production Features & Optimizations

This document summarizes the production-grade features added to vllmserver based on best practices from the Premai 2026 guide.

## New Modules

### `app/cache.py` — Model Discovery
Scans HuggingFace cache and extracts detailed model metadata:
- **Size** (GB on disk)
- **Architecture** (from model config)
- **Context length** (max_position_embeddings)
- **Parameters** (estimated from hidden_size × layers × vocab_size)
- **Quantization type** (AWQ, GPTQ, INT8)

Used by `/v1/models/detailed` endpoint to dynamically list all cached models.

### `app/auth.py` — API Key Authentication
Simple but extensible API key validation:
- Extract `X-API-Key` header from request
- Validate against allowed keys
- Return tier (dev/prod)
- Production: replace with database or HashiCorp Vault

### `app/rate_limit.py` — Token-Aware Rate Limiting
Track **three dimensions** of usage instead of just request count:
1. **RPM** (Requests Per Minute) — limit rapid-fire abuse
2. **TPM** (Tokens Per Minute) — prevent GPU monopolization  
3. **TPD** (Tokens Per Day) — account cost tracking

Why: A 50-word prompt and a 10,000-word document both count as 1 request, but the latter uses 200x more GPU. Token-aware limits are fair.

Implementation: In-memory (production should use Redis for distributed limiting across workers).

### `app/metrics.py` — Observability & Prometheus
Export LLM-specific metrics for dashboarding:
- **TTFT** (Time To First Token) — perceived responsiveness
- **Time Per Token** — generation throughput
- **Queue depth** — capacity indicator
- **GPU/KV cache utilization** — memory pressure
- **Request duration** — E2E latency
- **Token counts** — input/output tracking for billing

All metrics labeled by model, endpoint, and error type for filtering.

### `app/routers/models.py` — Model Discovery Endpoint
Two new endpoints:

**`GET /v1/models/detailed`** — Full model specifications
```json
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
  }
}
```

**`GET /v1/rate-limits`** — Current usage for authenticated user
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

## Updated Modules

### `app/models.py`
Added Pydantic schemas:
- `ModelCapabilities` — streaming, system prompt support
- `ModelLimits` — RPM, TPM, TPD, batch size
- `DetailedModelInfo` — full model card
- `RateLimitStatus` — current usage

### `app/routers/chat.py`
Enhanced with:
- API key validation (optional)
- Token-aware rate limiting check
- Metrics tracking (RequestTimer context manager)
- Token counting for prompt + completion
- Per-user request tracking

### `app/main.py`
Added:
- `/metrics` endpoint (Prometheus)
- Models router inclusion
- Prometheus REGISTRY integration

### `pyproject.toml`
Added dependencies:
- `huggingface-hub>=0.22.0` — HF cache scanning
- `prometheus-client>=0.20.0` — metrics export

## Authentication Flow

1. Request arrives with optional `X-API-Key: sk-prod-primary`
2. If provided, validate against `APIKeyValidator.ALLOWED_KEYS`
3. Reject (401) if invalid; allow (200) if valid or missing (for demo mode)
4. Store user/tier in `request.state` for downstream use

Production: Replace `ALLOWED_KEYS` dict with database lookup or cryptographic verification.

## Rate Limiting Flow

1. Extract estimated tokens: `(prompt_words + 50) + max_tokens`
2. Check if user has capacity in RPM, TPM, TPD buckets
3. Return 429 (Too Many Requests) if any bucket exceeded
4. Record usage for future requests from same user
5. Expire old entries after 1 minute (RPM) or 1 day (TPD)

Production: Move to Redis with pub/sub for distributed systems:
```python
# Each worker checks Redis for current user usage
# Atomically increments counter (prevents race conditions)
# TTL handles bucket expiry
```

## Metrics Collection

**TTFT tracking** (Time To First Token):
- Measures delay from request receipt to first output token
- Indicator of end-user perceived latency
- Typical goal: <500ms for good UX

**Throughput tracking** (Tokens/sec):
- Time between consecutive tokens during generation
- Typical: 50-150 tokens/sec on RTX 4090

**Queue depth**:
- Requests waiting for GPU availability
- High depth = overloaded system

All metrics exported to `/metrics` for:
- Prometheus scraping
- Grafana dashboards
- Datadog/New Relic integration
- CloudWatch custom metrics

## HuggingFace Cache Scanning

The `scan_huggingface_cache()` function:
1. Uses `huggingface_hub.scan_cache_dir()`
2. Filters for model type (not datasets)
3. Extracts model size from revision info
4. Loads `config.json` for architecture details
5. Infers quantization from model_id tags

Limitations:
- Scans once at server start (cached in memory)
- For hot-reload, restart server
- Production: add `/refresh-cache` admin endpoint

## Configuration

### Default Limits (editable in `app/rate_limit.py`)
```python
limiter = TokenRateLimiter(
    rpm_limit=60,          # 60 requests per minute
    tpm_limit=100000,      # 100k tokens per minute
    tpd_limit=10000000,    # 10M tokens per day
)
```

### Default API Keys (edit in `app/auth.py`)
```python
ALLOWED_KEYS = {
    "sk-dev-test": "development",
    "sk-prod-primary": "production",
}
```

## Usage Examples

### List all models with specs
```bash
curl http://localhost:8000/v1/models/detailed | jq '.data[] | {id, size_gb, quantization}'
```

### Check rate limit status
```bash
curl -H "X-API-Key: sk-prod-primary" \
  http://localhost:8000/v1/rate-limits
```

### Prometheus metrics
```bash
# In Grafana:
# - rate(llm_time_to_first_token_seconds[1m])
# - histogram_quantile(0.99, rate(llm_request_duration_seconds[5m]))
# - rate(llm_tokens_generated_total[1m])
```

### Python client with auth
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-prod-primary",  # Now validated!
    default_headers={
        "X-API-Key": "sk-prod-primary"
    }
)
```

## Production Checklist

- [ ] Replace in-memory rate limiter with Redis for distributed workers
- [ ] Replace `APIKeyValidator.ALLOWED_KEYS` with database/Vault
- [ ] Set realistic RPM/TPM/TPD limits based on your GPU
- [ ] Deploy Prometheus + Grafana for metrics dashboards
- [ ] Configure alerting (e.g., queue_depth > 10)
- [ ] Add request signing/JWT for user-facing deployments
- [ ] Set up log aggregation (ELK, Datadog)
- [ ] Add `/health` extended checks (GPU memory, model status)
- [ ] Implement model hot-reloading via admin API
- [ ] Test rate limiting with load (k6, JMeter)
