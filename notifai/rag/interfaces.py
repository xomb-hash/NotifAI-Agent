from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from notifai.core.schemas import Chunk, RetrievalResult


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_one(self, text: str) -> List[float]:
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
    def upsert(self, chunks: List[Chunk]) -> None:
        pass

    @abstractmethod
    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        metadata_filter: Optional[Dict[str, Any]] = None,
        relevance_threshold: float = 0.0,
    ) -> List[RetrievalResult]:
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        pass

    @abstractmethod
    def get_by_metadata(self, metadata_filter: Dict[str, Any]) -> List[Chunk]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass