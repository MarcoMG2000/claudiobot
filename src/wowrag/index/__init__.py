"""Index layer: offline indexing pipeline.

Consumers depend on this package, not on the internal module. Re-exports
``IndexingPipeline`` (R20).
"""

from wowrag.index.pipeline import IndexingPipeline

__all__ = ["IndexingPipeline"]
