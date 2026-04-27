"""Entry point for vLLM Inference Server."""

import logging
import multiprocessing
import sys

import uvicorn

from app.config import settings
from app.platform_detect import USE_MOCK_VLLM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Start the vLLM inference server.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Set multiprocessing start method for CUDA safety
        # 'spawn' prevents CUDA reinitialization in forked subprocesses
        if not USE_MOCK_VLLM:
            try:
                multiprocessing.set_start_method('spawn', force=True)
            except RuntimeError:
                # Already set, which is fine
                pass

        logger.info("Starting vLLM Inference Server")
        logger.info("Host: %s, Port: %d", settings.host, settings.port)
        logger.info("Chat Model: %s", settings.chat_model)
        if settings.embedding_model:
            logger.info("Embedding Model: %s", settings.embedding_model)

        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level,
            workers=1,  # vLLM manages its own async concurrency
        )
        return 0
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        return 0
    except Exception as e:
        logger.exception("Failed to start server: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
