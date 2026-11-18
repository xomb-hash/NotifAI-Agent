"""ChromaDB-backed vector store implementation.

The chromadb import is deferred to __init__ so this module can be imported
in environments without chromadb installed (e.g. unit tests).
"""

from __future__ import annotations

import logging
from typing import Any

from notifai.config.settings import settings
from notifai.core.schemas import Chunk, RetrievalResult
from notifai.rag.interfaces import VectorStore

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorStore):
    """ChromaDB vector store for development and small deployments."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection_name: str | None = None,
    ) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._host = host or settings.chroma_host
        self._port = port or settings.chroma_port
        self._collection_name = collection_name or settings.chroma_collection

        self._client = chromadb.HttpClient(
            host=self._host,
            port=self._port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaVectorStore initialized: %s:%s/%s",
            self._host,
            self._port,
            self._collection_name,
        )

    def upsert(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        ids = [c.id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]
        embeddings = [c.embedding for c in chunks if c.embedding is not None]

        if len(embeddings) == len(chunks):
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        else:
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        relevance_threshold: float = 0.0,
    ) -> list[RetrievalResult]:
        where_clause = _build_where_clause(metadata_filter) if metadata_filter else None

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
        )

        retrieval_results: list[RetrievalResult] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i in range(len(ids)):
            distance = distances[i] if i < len(distances) else 1.0
            score = 1.0 - distance

            if score < relevance_threshold:
                continue

            chunk = Chunk(
                id=ids[i],
                content=documents[i] if i < len(documents) else "",
                metadata=metadatas[i] if i < len(metadatas) else {},
            )
            retrieval_results.append(RetrievalResult(chunk=chunk, score=score))

        return retrieval_results

    def delete(self, ids: list[str]) -> None:
        if ids:
            self._collection.delete(ids=ids)

    def get_by_metadata(self, metadata_filter: dict[str, Any]) -> list[Chunk]:
        where_clause = _build_where_clause(metadata_filter)
        results = self._collection.get(where=where_clause)

        chunks: list[Chunk] = []
        ids = results.get("ids", [[]])
        documents = results.get("documents", [[]])
        metadatas = results.get("metadatas", [[]])

        for i in range(len(ids)):
            chunks.append(
                Chunk(
                    id=ids[i],
                    content=documents[i] if i < len(documents) else "",
                    metadata=metadatas[i] if i < len(metadatas) else {},
                )
            )
        return chunks

    def health_check(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False

    def count(self) -> int:
        return self._collection.count()


def _build_where_clause(filters: dict[str, Any]) -> dict[str, Any]:
    conditions: list[dict[str, Any]] = []
    for key, value in filters.items():
        if isinstance(value, dict):
            conditions.append({key: value})
        else:
            conditions.append({key: {"$eq": value}})

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}
