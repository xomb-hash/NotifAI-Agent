"""RAG pipeline: ingestion, embedding, storage, and retrieval."""

from __future__ import annotations

import logging
from typing import Any

from notifai.config.settings import settings
from notifai.core.schemas import Chunk, CollegeEvent, RetrievalResult
from notifai.rag.chunking import chunk_notice
from notifai.rag.embeddings import GeminiEmbeddingProvider
from notifai.rag.interfaces import EmbeddingProvider, VectorStore
from notifai.rag.vector_store_chroma import ChromaVectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """End-to-end RAG pipeline for ingesting, embedding, storing, and retrieving notices."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._embedder = embedding_provider or GeminiEmbeddingProvider()
        self._store = vector_store or ChromaVectorStore()

    def ingest(
        self,
        text: str,
        events: list[CollegeEvent] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Ingest a notice (raw text + optional structured events) into the vector store."""
        chunks = chunk_notice(
            text=text,
            events=events,
            metadata=metadata,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )

        if not chunks:
            logger.debug("No chunks produced from notice, skipping ingestion")
            return 0

        _embed_chunks(chunks, self._embedder)
        self._store.upsert(chunks)
        logger.info("Ingested %d chunks into vector store", len(chunks))
        return len(chunks)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
        relevance_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve relevant chunks for a query."""
        top_k = top_k or settings.top_k
        relevance_threshold = (
            relevance_threshold
            if relevance_threshold is not None
            else settings.relevance_threshold
        )

        query_embedding = self._embedder.embed_one(query)
        results = self._store.query(
            query_embedding=query_embedding,
            top_k=top_k,
            metadata_filter=metadata_filter,
            relevance_threshold=relevance_threshold,
        )

        logger.debug(
            "Retrieved %d results for query (threshold=%.2f)",
            len(results),
            relevance_threshold,
        )
        return results

    def retrieve_deadlines_this_week(self) -> list[RetrievalResult]:
        """Retrieve events/deadlines scheduled within the current week."""
        from datetime import date, timedelta

        today = date.today()
        week_end = today + timedelta(days=7)

        results = self._store.get_by_metadata(
            {"data_type": "structured"}
        )

        filtered: list[RetrievalResult] = []
        for chunk in results:
            event_date = chunk.metadata.get("date", "")
            if event_date and today.isoformat() <= event_date <= week_end.isoformat():
                filtered.append(
                    RetrievalResult(chunk=chunk, score=1.0)
                )

        return filtered

    def health_check(self) -> bool:
        return self._store.health_check()

    def count(self) -> int:
        if hasattr(self._store, "count"):
            return self._store.count()
        return 0


def _embed_chunks(chunks: list[Chunk], embedder: EmbeddingProvider) -> None:
    texts = [c.content for c in chunks]
    embeddings = embedder.embed(texts)
    for chunk, embedding in zip(chunks, embeddings, strict=False):
        chunk.embedding = embedding
