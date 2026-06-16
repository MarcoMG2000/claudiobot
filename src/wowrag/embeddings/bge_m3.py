"""Real bge-m3 embedding provider via FlagEmbedding.

The FlagEmbedding (and transitively torch / sentence-transformers) import
happens **inside ``__init__``**, not at module level, so this module is
importable without the ML dependencies installed (R9). The heavy stack is
only required when instantiating ``BgeM3Embeddings``.
"""

from __future__ import annotations

from wowrag.embeddings.base import EmbeddingError


class BgeM3Embeddings:
    """Real bge-m3 embedding provider via FlagEmbedding (lazy import).

    Produces dense vectors (``dense_vecs``) for the ``BAAI/bge-m3`` multilingual
    model. The module imports without FlagEmbedding installed; the dependency is
    only enforced at construction time.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        dimension: int = 1024,
        batch_size: int = 32,
        device: str = "cpu",
    ) -> None:
        try:
            from FlagEmbedding import BGEM3FlagModel  # lazy import (R9)
        except ImportError as exc:
            raise EmbeddingError(
                "FlagEmbedding is not installed. "
                "Install ML dependencies: pip install -r requirements-ml.txt"
            ) from exc

        if device == "cuda":
            import torch

            if not torch.cuda.is_available():
                raise EmbeddingError(
                    "embedding_device='cuda' requested but CUDA is not available."
                )  # R15

        self._dimension = dimension
        self._batch_size = batch_size
        self._model = BGEM3FlagModel(model_name, use_fp16=(device != "cpu"))

    @property
    def dimension(self) -> int:
        return self._dimension  # R11: no model call needed

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise EmbeddingError(
                    f"Text at position {i} is empty or whitespace-only."
                )  # R16
        # Process in batches to bound GPU memory usage (R5).
        result: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            output = self._model.encode(batch, batch_size=self._batch_size)
            result.extend(output["dense_vecs"].tolist())
        return result
