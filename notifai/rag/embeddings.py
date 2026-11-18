import time
from typing import List, Optional
from google import genai
from google.genai import types
from notifai.config.settings import settings
from notifai.rag.interfaces import EmbeddingProvider
from notifai.observability.tracing import record_embedding_metrics


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self._client = genai.Client(api_key=api_key or settings.google_api_key)
        self._model_name = model_name or settings.gemini_embedding_model
        self._dimension = 768

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        start_time = time.perf_counter()
        try:
            response = self._client.models.embed_content(
                model=self._model_name,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            embeddings = [e.values for e in response.embeddings]
            latency_ms = (time.perf_counter() - start_time) * 1000
            total_tokens = sum(len(t.split()) for t in texts) * 1.3
            record_embedding_metrics(
                model=self._model_name,
                tokens=int(total_tokens),
                latency_ms=latency_ms,
                success=True,
            )
            return embeddings
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            record_embedding_metrics(
                model=self._model_name,
                tokens=0,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )
            raise

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]