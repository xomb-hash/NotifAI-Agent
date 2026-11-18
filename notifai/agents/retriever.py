"""Retriever agent: RAG-based context retrieval."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from notifai.tools.rag_tool import (
    ingest_notice,
    retrieve_deadlines_this_week,
    retrieve_relevant_context,
)

logger = logging.getLogger(__name__)


class RetrieverInput(BaseModel):
    """Input for the Retriever agent."""

    query: str = Field(description="Search query")
    top_k: int = Field(default=5, description="Number of results")
    metadata_filter: dict[str, Any] | None = Field(
        default=None, description="Metadata filters"
    )


class RetrieverOutput(BaseModel):
    """Output from the Retriever agent."""

    results: list[dict[str, Any]] = Field(default_factory=list)
    deadlines: list[dict[str, Any]] = Field(default_factory=list)


def retrieve_context(
    query: str,
    top_k: int = 5,
    metadata_filter: dict[str, Any] | None = None,
) -> RetrieverOutput:
    """Retrieve relevant context for a query.

    This is the core business logic, independent of ADK.
    """
    results = retrieve_relevant_context(
        query=query,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )

    return RetrieverOutput(results=results, deadlines=[])


def retrieve_deadlines() -> RetrieverOutput:
    """Retrieve deadlines due this week."""
    deadlines = retrieve_deadlines_this_week()
    return RetrieverOutput(results=[], deadlines=deadlines)


def ingest_notice_for_rag(
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest a notice into the RAG pipeline."""
    return ingest_notice(text=text, metadata=metadata)
