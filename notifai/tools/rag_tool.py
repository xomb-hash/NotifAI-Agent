"""Typed RAG retrieval tool for the Retriever agent.

The RAGPipeline import is deferred to _get_pipeline so this module can be
imported in environments without chromadb/google-genai installed.
"""

from __future__ import annotations

import logging
from typing import Any

from notifai.core.schemas import RetrievalResult

logger = logging.getLogger(__name__)

_pipeline: Any = None


def _get_pipeline() -> Any:
    global _pipeline
    if _pipeline is None:
        from notifai.rag.pipeline import RAGPipeline

        _pipeline = RAGPipeline()
    return _pipeline


def retrieve_relevant_context(
    query: str,
    top_k: int = 5,
    metadata_filter: dict[str, Any] | None = None,
    relevance_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Retrieve relevant context chunks for a query.

    Args:
        query: The search query text.
        top_k: Number of results to return.
        metadata_filter: Optional metadata filters (e.g., {"source_chat": "Srijan"}).
        relevance_threshold: Minimum relevance score (0-1).

    Returns:
        List of dicts with chunk id, content, score, and metadata.
    """
    try:
        pipeline = _get_pipeline()
        results = pipeline.retrieve(
            query=query,
            top_k=top_k,
            metadata_filter=metadata_filter,
            relevance_threshold=relevance_threshold,
        )

        return [
            {
                "chunk_id": r.chunk.id,
                "content": r.chunk.content,
                "score": round(r.score, 4),
                "metadata": r.chunk.metadata,
            }
            for r in results
        ]
    except Exception as e:
        logger.error("RAG retrieval failed for query '%s': %s", query, e)
        return []


def retrieve_deadlines_this_week() -> list[dict[str, Any]]:
    """Retrieve all events/deadlines scheduled within the current week.

    Returns:
        List of dicts with event details.
    """
    try:
        pipeline = _get_pipeline()
        results = pipeline.retrieve_deadlines_this_week()

        return [
            {
                "chunk_id": r.chunk.id,
                "content": r.chunk.content,
                "score": round(r.score, 4),
                "metadata": r.chunk.metadata,
            }
            for r in results
        ]
    except Exception as e:
        logger.error("Failed to retrieve deadlines: %s", e)
        return []


def ingest_notice(
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest a notice into the RAG pipeline.

    Args:
        text: The raw notice text.
        metadata: Optional metadata (source_chat, source_sender, etc.).

    Returns:
        Dict with status and number of chunks ingested.
    """
    try:
        pipeline = _get_pipeline()
        count = pipeline.ingest(text=text, metadata=metadata)
        return {"status": "success", "chunks_ingested": count}
    except Exception as e:
        logger.error("Failed to ingest notice: %s", e)
        return {"status": "error", "error": str(e)}


def health_check() -> dict[str, Any]:
    """Check if the RAG pipeline is healthy."""
    try:
        pipeline = _get_pipeline()
        healthy = pipeline.health_check()
        count = pipeline.count()
        return {
            "status": "healthy" if healthy else "unhealthy",
            "chunks_stored": count,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}