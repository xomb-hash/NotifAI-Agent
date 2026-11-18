"""Text chunking for structured event data and unstructured raw messages."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from notifai.core.schemas import Chunk, CollegeEvent


def _hash_id(content: str, prefix: str = "chk") -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _chunk_by_sentences(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            while len(sentence) > chunk_size:
                chunks.append(sentence[:chunk_size])
                sentence = sentence[chunk_size - overlap :]
            current = sentence

    if current:
        chunks.append(current)
    return chunks


def chunk_raw_message(
    text: str,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """Split a raw message into overlapping sentence-based chunks."""
    metadata = metadata or {}
    chunks: list[Chunk] = []

    for idx, chunk_text in enumerate(_chunk_by_sentences(text, chunk_size, overlap)):
        chunk_metadata = {
            **metadata,
            "chunk_index": idx,
            "total_chunks": 0,
            "data_type": "unstructured",
        }
        chunks.append(
            Chunk(
                id=_hash_id(f"{chunk_text}_{idx}"),
                content=chunk_text,
                metadata=chunk_metadata,
            )
        )

    if chunks:
        total = len(chunks)
        for c in chunks:
            c.metadata["total_chunks"] = total

    return chunks


def chunk_event(event: CollegeEvent) -> Chunk:
    """Convert a structured CollegeEvent into a single searchable chunk."""
    content = (
        f"Title: {event.title}\n"
        f"Date: {event.date}\n"
        f"Time: {event.time}\n"
        f"Description: {event.description}\n"
        f"Type: {event.notice_type.value}\n"
        f"Status: {event.status.value}"
    )
    return Chunk(
        id=_hash_id(f"{event.id}_{event.title}", prefix="evt"),
        content=content,
        metadata={
            "data_type": "structured",
            "event_id": event.id,
            "title": event.title,
            "date": event.date,
            "time": event.time,
            "notice_type": event.notice_type.value,
            "status": event.status.value,
            "source_message_id": event.source_message_id or "",
            "source_chat": event.source_chat or "",
            "source_sender": event.source_sender or "",
            "confidence": event.confidence,
            "source_timestamp": (
                event.source_timestamp.isoformat() if event.source_timestamp else ""
            ),
        },
    )


def chunk_events(events: list[CollegeEvent]) -> list[Chunk]:
    """Convert a list of CollegeEvents into searchable chunks."""
    return [chunk_event(e) for e in events]


def chunk_notice(
    text: str,
    events: list[CollegeEvent] | None = None,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """Chunk a notice that has both raw text and structured events."""
    all_chunks: list[Chunk] = []

    if events:
        all_chunks.extend(chunk_events(events))

    if text and text.strip():
        raw_metadata = {**(metadata or {}), "has_events": bool(events)}
        all_chunks.extend(
            chunk_raw_message(text, raw_metadata, chunk_size, overlap)
        )

    return all_chunks