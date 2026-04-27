"""Scan HuggingFace cache and extract model metadata."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from huggingface_hub import scan_cache_dir

logger = logging.getLogger(__name__)


class ModelMetadata:
    """Extracted metadata for a cached model."""

    def __init__(
        self,
        model_id: str,
        size_bytes: int,
        tags: list[str],
        config: dict[str, Any],
    ) -> None:
        self.model_id = model_id
        self.size_bytes = size_bytes
        self.size_gb = round(size_bytes / (1024**3), 2)
        self.tags = tags
        self.config = config

    @property
    def architecture(self) -> str:
        return self.config.get("architectures", ["unknown"])[0] if self.config else "unknown"

    @property
    def context_length(self) -> int:
        cfg = self.config or {}
        return cfg.get("max_position_embeddings", cfg.get("seq_length", 2048))

    @property
    def hidden_size(self) -> int:
        return self.config.get("hidden_size", 0) if self.config else 0

    @property
    def num_parameters(self) -> int:
        """Estimate number of parameters from config."""
        if not self.config:
            return 0
        hidden = self.config.get("hidden_size", 0)
        num_layers = self.config.get("num_hidden_layers", 0)
        vocab_size = self.config.get("vocab_size", 0)
        if hidden and num_layers and vocab_size:
            return hidden * hidden * 4 * num_layers + vocab_size * hidden
        return 0

    @property
    def is_quantized(self) -> bool:
        if not self.tags:
            return False
        return any(q in self.tags for q in ["awq", "gptq", "int8", "int4"])

    @property
    def quantization_type(self) -> Optional[str]:
        if not self.tags:
            return None
        for q in ["awq", "gptq", "int8", "int4"]:
            if q in self.tags:
                return q.upper()
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "size_gb": self.size_gb,
            "architecture": self.architecture,
            "context_length": self.context_length,
            "num_parameters": self.num_parameters,
            "hidden_size": self.hidden_size,
            "is_quantized": self.is_quantized,
            "quantization_type": self.quantization_type,
            "tags": self.tags,
        }


def _load_model_config(model_path: Path) -> Optional[dict[str, Any]]:
    """Load config.json from model directory."""
    config_file = model_path / "config.json"
    if not config_file.exists():
        return None
    try:
        with open(config_file) as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"Failed to load config for {model_path}: {e}")
        return None


def scan_huggingface_cache() -> dict[str, ModelMetadata]:
    """Scan HF cache and return model metadata indexed by model_id."""
    models: dict[str, ModelMetadata] = {}

    try:
        cache_info = scan_cache_dir()
    except Exception as e:
        logger.warning(f"Failed to scan HF cache: {e}")
        return models

    for repo in cache_info.repos:
        model_id = repo.repo_id
        if repo.repo_type != "model":
            continue

        total_size = sum(r.size_on_disk for r in repo.revisions if r.size_on_disk)
        config = None
        tags: list[str] = []

        # Try to extract tags from model_id
        if "awq" in model_id.lower():
            tags.append("awq")
        if "gptq" in model_id.lower():
            tags.append("gptq")
        if "gguf" in model_id.lower():
            tags.append("gguf")

        # Try to load config.json from the latest revision
        if repo.revisions:
            # revisions is a frozenset, convert to list
            revisions_list = list(repo.revisions)
            if revisions_list:
                latest_rev = revisions_list[0]
                if hasattr(latest_rev, 'snapshot_path') and latest_rev.snapshot_path:
                    config = _load_model_config(Path(latest_rev.snapshot_path))

        models[model_id] = ModelMetadata(model_id, total_size, tags, config or {})

    logger.info(f"Scanned HF cache: found {len(models)} models")
    return models
