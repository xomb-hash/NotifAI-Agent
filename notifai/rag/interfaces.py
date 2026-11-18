from abc import ABC, abstractmethod
from typing import Any

from notifai.core.schemas import Chunk, RetrievalResult


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_one(self, text: str) -> list[float]:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> None:
        pass

    @abstractmethod
    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
        relevance_threshold: float = 0.0,
    ) -> list[RetrievalResult]:
        pass

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        pass

    @abstractmethod
    def get_by_metadata(self, metadata_filter: dict[str, Any]) -> list[Chunk]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass
