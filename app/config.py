import os
from typing import Optional


class Settings:
    def __init__(self) -> None:
        # Chat model
        self.chat_model: str = os.environ.get("CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ")
        self.chat_gpu_memory_utilization: float = float(os.environ.get("CHAT_GPU_MEM_UTIL", "0.7"))
        self.chat_max_model_len: int = int(os.environ.get("CHAT_MAX_MODEL_LEN", "4096"))
        self.chat_max_num_seqs: int = int(os.environ.get("CHAT_MAX_NUM_SEQS", "256"))
        self.chat_tensor_parallel_size: int = int(os.environ.get("CHAT_TENSOR_PARALLEL", "1"))
        self.chat_quantization: Optional[str] = os.environ.get("CHAT_QUANTIZATION") or None
        self.chat_dtype: str = os.environ.get("CHAT_DTYPE", "auto")

        # Embedding model (optional — disabled if EMBEDDING_MODEL is not set)
        self.embedding_model: Optional[str] = os.environ.get("EMBEDDING_MODEL") or None
        self.embedding_gpu_memory_utilization: float = float(
            os.environ.get("EMBEDDING_GPU_MEM_UTIL", "0.2")
        )
        self.embedding_max_model_len: int = int(os.environ.get("EMBEDDING_MAX_MODEL_LEN", "512"))
        self.embedding_tensor_parallel_size: int = int(
            os.environ.get("EMBEDDING_TENSOR_PARALLEL", "1")
        )

        # Server
        self.host: str = os.environ.get("HOST", "0.0.0.0")
        self.port: int = int(os.environ.get("PORT", "8000"))
        self.log_level: str = os.environ.get("LOG_LEVEL", "info")


settings = Settings()
