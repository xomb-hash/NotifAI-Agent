"""Tests for core Pydantic schemas."""


import pytest

from notifai.core.schemas import (
    Chunk,
    CollegeEvent,
    CollegeEventList,
    EventStatus,
    NoticeType,
    SessionState,
)


class TestCollegeEvent:
    def test_valid_event(self) -> None:
        event = CollegeEvent(
            is_important_notice=True,
            title="Team Meeting",
            date="2026-11-20",
            time="10:00",
            description="Weekly sync",
        )
        assert event.title == "Team Meeting"
        assert event.status == EventStatus.PENDING
        assert event.notice_type == NoticeType.EVENT

    def test_invalid_date_format(self) -> None:
        with pytest.raises(ValueError):
            CollegeEvent(
                is_important_notice=True,
                title="Test",
                date="11/20/2026",
                time="10:00",
                description="Bad date",
            )

    def test_invalid_time_format(self) -> None:
        with pytest.raises(ValueError):
            CollegeEvent(
                is_important_notice=True,
                title="Test",
                date="2026-11-20",
                time="10:00 AM",
                description="Bad time",
            )

    def test_event_with_source_metadata(self) -> None:
        event = CollegeEvent(
            is_important_notice=True,
            title="Class",
            date="2026-11-20",
            time="09:00",
            description="Lecture",
            source_chat="Srijan",
            source_sender="Prof",
            confidence=0.95,
        )
        assert event.source_chat == "Srijan"
        assert event.confidence == 0.95


class TestCollegeEventList:
    def test_empty_list(self) -> None:
        lst = CollegeEventList()
        assert lst.events == []

    def test_list_with_events(self) -> None:
        lst = CollegeEventList(
            events=[
                CollegeEvent(
                    is_important_notice=True,
                    title="A",
                    date="2026-11-20",
                    time="10:00",
                    description="Test",
                )
            ]
        )
        assert len(lst.events) == 1


class TestChunk:
    def test_chunk_creation(self) -> None:
        chunk = Chunk(content="Hello world", metadata={"type": "test"})
        assert chunk.content == "Hello world"
        assert chunk.metadata["type"] == "test"
        assert chunk.id is not None


class TestSessionState:
    def test_initial_state(self) -> None:
        state = SessionState()
        assert state.current_step == "router"
        assert state.extracted_events == []
        assert state.validation_retries == 0
        assert state.max_validation_retries == 2

    def test_update_step(self) -> None:
        state = SessionState()
        state.update_step("extractor")
        assert state.current_step == "extractor"

    def test_add_error(self) -> None:
        state = SessionState()
        state.add_error("Test error")
        assert len(state.errors) == 1
        assert "Test error" in state.errors[0]
