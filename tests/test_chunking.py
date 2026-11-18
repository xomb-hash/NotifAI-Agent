"""Tests for the RAG chunking module."""

from notifai.core.schemas import CollegeEvent
from notifai.rag.chunking import (
    chunk_event,
    chunk_events,
    chunk_notice,
    chunk_raw_message,
)


class TestChunkRawMessage:
    def test_short_message_single_chunk(self) -> None:
        chunks = chunk_raw_message("Meeting at 10am tomorrow.")
        assert len(chunks) == 1
        assert chunks[0].metadata["data_type"] == "unstructured"
        assert "Meeting" in chunks[0].content

    def test_long_message_multiple_chunks(self) -> None:
        text = " ".join(f"Sentence number {i}." for i in range(50))
        chunks = chunk_raw_message(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1
        assert all(c.metadata["data_type"] == "unstructured" for c in chunks)

    def test_metadata_propagated(self) -> None:
        chunks = chunk_raw_message(
            "Test message", metadata={"source_chat": "Srijan"}
        )
        assert chunks[0].metadata["source_chat"] == "Srijan"

    def test_chunk_indices_and_total(self) -> None:
        text = " ".join(f"Sentence {i}." for i in range(30))
        chunks = chunk_raw_message(text, chunk_size=50, overlap=10)
        assert len(chunks) > 1
        for i, c in enumerate(chunks):
            assert c.metadata["chunk_index"] == i
            assert c.metadata["total_chunks"] == len(chunks)


class TestChunkEvent:
    def test_event_chunk_has_structured_metadata(self) -> None:
        event = CollegeEvent(
            is_important_notice=True,
            title="Team Meeting",
            date="2026-11-20",
            time="10:00",
            description="Weekly sync",
        )
        chunk = chunk_event(event)
        assert chunk.metadata["data_type"] == "structured"
        assert chunk.metadata["title"] == "Team Meeting"
        assert chunk.metadata["date"] == "2026-11-20"
        assert "Team Meeting" in chunk.content

    def test_chunk_events_list(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title=f"Event {i}",
                date="2026-11-20",
                time="10:00",
                description="Test",
            )
            for i in range(3)
        ]
        chunks = chunk_events(events)
        assert len(chunks) == 3
        assert all(c.metadata["data_type"] == "structured" for c in chunks)


class TestChunkNotice:
    def test_text_only(self) -> None:
        chunks = chunk_notice("Simple notice text")
        assert len(chunks) == 1
        assert chunks[0].metadata["data_type"] == "unstructured"

    def test_events_only(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Exam",
                date="2026-11-25",
                time="09:00",
                description="Final exam",
            )
        ]
        chunks = chunk_notice("", events=events)
        assert len(chunks) == 1
        assert chunks[0].metadata["data_type"] == "structured"

    def test_text_and_events(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Meet",
                date="2026-11-20",
                time="14:00",
                description="Sync",
            )
        ]
        chunks = chunk_notice("Raw message context here.", events=events)
        assert len(chunks) == 2
        types = {c.metadata["data_type"] for c in chunks}
        assert types == {"structured", "unstructured"}

    def test_empty_notice(self) -> None:
        chunks = chunk_notice("")
        assert len(chunks) == 0