"""Gemini embedding provider.

The google-genai imports are deferred to call time so this module can be
imported in environments without the Google SDK installed (e.g. unit tests).
"""

from __future__ import annotations

import time
from typing import Any

from notifai.config.settings import settings
from notifai.rag.interfaces import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by the Gemini text-embedding model."""

    def __init__(
        self, api_key: str | None = None, model_name: str | None = None
    ) -> None:
        self._api_key = api_key or settings.google_api_key
        self._model_name = model_name or settings.gemini_embedding_model
        self._dimension = 768
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        from google.genai import types

        client = self._get_client()
        start_time = time.perf_counter()
        try:
            response = client.models.embed_content(
                model=self._model_name,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            embeddings = [e.values for e in response.embeddings]
            latency_ms = (time.perf_counter() - start_time) * 1000
            total_tokens = int(sum(len(t.split()) for t in texts) * 1.3)
            _record_embedding_metrics(
                model=self._model_name,
                tokens=total_tokens,
                latency_ms=latency_ms,
                success=True,
            )
            return embeddings
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            _record_embedding_metrics(
                model=self._model_name,
                tokens=0,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )
            raise

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


def _record_embedding_metrics(
    model: str,
    tokens: int,
    latency_ms: float,
    success: bool,
    error: str = "",
) -> None:
    """Record embedding metrics if tracing is active."""
    try:
        from notifai.observability.tracing import record_agent_call

        record_agent_call(
            name=f"embedding:{model}",
            latency_ms=latency_ms,
            tokens_in=tokens,
            success=success,
            error=error,
        )
    except Exception:
        pass