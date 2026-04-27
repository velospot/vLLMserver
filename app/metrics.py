"""LLM-specific observability metrics for Prometheus."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from prometheus_client import Counter, Gauge, Histogram

# Request metrics
requests_total = Counter(
    "llm_requests_total",
    "Total number of requests",
    ["endpoint", "status"],
)

requests_in_flight = Gauge(
    "llm_requests_in_flight",
    "Requests currently being processed",
    ["endpoint"],
)

queue_depth = Gauge(
    "llm_queue_depth",
    "Number of requests waiting in queue",
)

# Token metrics
tokens_generated = Counter(
    "llm_tokens_generated_total",
    "Total tokens generated",
    ["model"],
)

tokens_received = Counter(
    "llm_tokens_received_total",
    "Total prompt tokens received",
    ["model"],
)

# Performance metrics (Prometheus histograms automatically track sum, count, and bucket counts)
time_to_first_token = Histogram(
    "llm_time_to_first_token_seconds",
    "Time from request to first generated token (latency perception)",
    ["model"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
)

time_per_token = Histogram(
    "llm_time_per_token_seconds",
    "Time to generate each token (throughput)",
    ["model"],
    buckets=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0],
)

request_duration = Histogram(
    "llm_request_duration_seconds",
    "Total request duration including queue wait and generation",
    ["endpoint", "status"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

gpu_utilization = Gauge(
    "llm_gpu_utilization_percent",
    "GPU memory utilization percentage",
    ["device"],
)

kv_cache_usage = Gauge(
    "llm_kv_cache_usage_percent",
    "KV cache utilization percentage",
    ["model"],
)

# Error metrics
errors_total = Counter(
    "llm_errors_total",
    "Total number of errors",
    ["endpoint", "error_type"],
)


class RequestTimer:
    """Context manager for tracking request metrics."""

    def __init__(self, endpoint: str, model: str) -> None:
        self.endpoint = endpoint
        self.model = model
        self.start_time: float = 0
        self.first_token_time: Optional[float] = None

    def __enter__(self) -> RequestTimer:
        self.start_time = time.time()
        requests_in_flight.labels(endpoint=self.endpoint).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed = time.time() - self.start_time
        status = "error" if exc_type else "success"
        requests_total.labels(endpoint=self.endpoint, status=status).inc()
        request_duration.labels(endpoint=self.endpoint, status=status).observe(elapsed)
        requests_in_flight.labels(endpoint=self.endpoint).dec()

    @asynccontextmanager
    async def track_ttft(self) -> AsyncIterator[None]:
        """Track time to first token during streaming."""
        ttft_start = time.time()
        first_token_recorded = False

        async def _yield() -> None:
            nonlocal first_token_recorded
            if not first_token_recorded:
                ttft = time.time() - ttft_start
                time_to_first_token.labels(model=self.model).observe(ttft)
                first_token_recorded = True

        yield

        # Ensure TTFT is recorded even if generator isn't consumed
        if not first_token_recorded:
            await _yield()
