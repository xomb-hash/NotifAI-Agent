"""Tests for the multi-agent system."""

from unittest.mock import MagicMock, patch

from notifai.core.schemas import CollegeEvent


class TestValidator:
    def test_valid_events_pass(self) -> None:
        from notifai.agents.validator import validate_events

        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Team Meeting",
                date="2026-11-20",
                time="10:00",
                description="Weekly sync",
            )
        ]
        result = validate_events(events, "Team meeting at 10am tomorrow")
        assert result.is_valid
        assert len(result.corrected_events) == 1

    def test_empty_events_pass(self) -> None:
        from notifai.agents.validator import validate_events

        result = validate_events([], "No events here")
        assert result.is_valid
        assert result.retry_needed is False

    def test_hallucinated_event_flagged(self) -> None:
        from notifai.agents.validator import validate_events

        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Submit Assignment",
                date="2026-11-20",
                time="10:00",
                description="Submit your assignment",
            )
        ]
        result = validate_events(events, "Just having coffee")
        assert not result.is_valid
        assert len(result.issues) > 0
        assert result.retry_needed

    def test_duplicate_events_flagged(self) -> None:
        from notifai.agents.validator import validate_events

        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Meeting",
                date="2026-11-20",
                time="10:00",
                description="Team sync",
            ),
            CollegeEvent(
                is_important_notice=True,
                title="Meeting",
                date="2026-11-20",
                time="10:00",
                description="Team sync",
            ),
        ]
        result = validate_events(events, "Meeting at 10am")
        assert not result.is_valid
        assert any("Duplicate" in issue for issue in result.issues)

    def test_empty_title_flagged(self) -> None:
        from notifai.agents.validator import validate_events

        events = [
            CollegeEvent(
                is_important_notice=True,
                title="",
                date="2026-11-20",
                time="10:00",
                description="Something",
            )
        ]
        result = validate_events(events, "Something at 10am")
        assert not result.is_valid
        assert any("empty" in issue.lower() or "short" in issue.lower() for issue in result.issues)


class TestScheduler:
    def test_empty_events(self) -> None:
        from notifai.agents.scheduler import schedule_validated_events

        result = schedule_validated_events([])
        assert result.scheduled_count == 0
        assert result.results == []

    def test_dry_run(self) -> None:
        from notifai.agents.scheduler import schedule_validated_events

        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Test",
                date="2026-11-20",
                time="10:00",
                description="Test event",
            )
        ]
        result = schedule_validated_events(events, dry_run=True)
        assert result.scheduled_count == 0
        assert len(result.results) == 1
        assert result.results[0]["status"] == "dry_run"

    @patch("notifai.agents.scheduler.schedule_event")
    def test_schedule_with_mock(self, mock_schedule: MagicMock) -> None:
        from notifai.agents.scheduler import schedule_validated_events

        mock_schedule.return_value = {
            "status": "scheduled",
            "event_id": "abc123",
            "html_link": "https://calendar.google.com/event/abc123",
        }

        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Test Event",
                date="2026-11-20",
                time="10:00",
                description="Test",
            )
        ]
        result = schedule_validated_events(events)
        assert result.scheduled_count == 1
        mock_schedule.assert_called_once()


class TestRouter:
    @patch("notifai.agents.router.extract_events")
    @patch("notifai.agents.router.retrieve_context")
    @patch("notifai.agents.router.schedule_validated_events")
    def test_route_no_events(
        self,
        mock_schedule: MagicMock,
        mock_retrieve: MagicMock,
        mock_extract: MagicMock,
    ) -> None:
        from notifai.agents.extractor import ExtractionOutput
        from notifai.agents.retriever import RetrieverOutput
        from notifai.agents.router import route_message

        mock_retrieve.return_value = RetrieverOutput(results=[], deadlines=[])
        mock_extract.return_value = ExtractionOutput(
            events=[],
            model_used="gemini-3.5-flash-lite",
            tokens_in=100,
            tokens_out=50,
            latency_ms=200.0,
            cost_usd=0.001,
        )

        result = route_message(
            message="Hello world",
            enable_rag=False,
            enable_validation=False,
        )

        assert result.final_events == []
        assert result.extraction is not None
        assert result.extraction.events == []

    @patch("notifai.agents.router.extract_events")
    @patch("notifai.agents.router.schedule_validated_events")
    def test_route_full_pipeline(
        self,
        mock_schedule: MagicMock,
        mock_extract: MagicMock,
    ) -> None:
        from notifai.agents.extractor import ExtractionOutput
        from notifai.agents.router import route_message
        from notifai.agents.scheduler import SchedulerOutput

        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Team Meeting",
                date="2026-11-20",
                time="10:00",
                description="Weekly sync",
            )
        ]

        mock_extract.return_value = ExtractionOutput(
            events=events,
            model_used="gemini-3.5-flash-lite",
            tokens_in=200,
            tokens_out=100,
            latency_ms=300.0,
            cost_usd=0.002,
        )
        mock_schedule.return_value = SchedulerOutput(
            scheduled_count=1,
            results=[{"status": "scheduled", "event_id": "abc"}],
            errors=[],
        )

        result = route_message(
            message="Team meeting at 10am tomorrow",
            enable_rag=False,
            enable_validation=True,
            dry_run=True,
        )

        assert len(result.final_events) == 1
        assert result.extraction is not None
        assert result.validation is not None

    @patch("notifai.agents.router.extract_events")
    @patch("notifai.agents.router.retrieve_context")
    def test_route_with_retrieval(
        self,
        mock_retrieve: MagicMock,
        mock_extract: MagicMock,
    ) -> None:
        from notifai.agents.extractor import ExtractionOutput
        from notifai.agents.retriever import RetrieverOutput
        from notifai.agents.router import route_message

        mock_retrieve.return_value = RetrieverOutput(
            results=[
                {"chunk_id": "c1", "content": "context", "score": 0.9, "metadata": {}}
            ],
            deadlines=[],
        )
        mock_extract.return_value = ExtractionOutput(
            events=[],
            model_used="gemini-3.5-flash-lite",
            tokens_in=100,
            tokens_out=50,
            latency_ms=200.0,
            cost_usd=0.001,
        )

        result = route_message(
            message="Test",
            enable_rag=True,
            enable_validation=False,
        )

        assert result.retrieval is not None
        assert len(result.retrieval.results) == 1


class TestSessionState:
    def test_state_transitions(self) -> None:
        from notifai.core.schemas import SessionState

        state = SessionState()
        assert state.current_step == "router"

        state.update_step("extractor")
        assert state.current_step == "extractor"

        state.update_step("validator")
        assert state.current_step == "validator"

        state.update_step("done")
        assert state.current_step == "done"

    def test_error_accumulation(self) -> None:
        from notifai.core.schemas import SessionState

        state = SessionState()
        state.add_error("First error")
        state.add_error("Second error")
        assert len(state.errors) == 2


class TestTracing:
    def test_trace_lifecycle(self) -> None:
        from notifai.observability.tracing import (
            end_trace,
            record_agent_call,
            start_trace,
        )

        start_trace(request_id="test-1", session_id="sess-1")
        record_agent_call("extractor", 100.0, tokens_in=100, tokens_out=50, cost_usd=0.001)
        record_agent_call("validator", 50.0, success=True)
        result = end_trace()

        assert result is not None
        assert result["request_id"] == "test-1"
        assert result["total_tokens_in"] == 100
        assert result["total_tokens_out"] == 50
        assert len(result["agents"]) == 2

    def test_metrics_summary(self) -> None:
        from notifai.observability.tracing import (
            end_trace,
            get_metrics_summary,
            record_agent_call,
            reset_traces,
            start_trace,
        )

        reset_traces()

        for i in range(3):
            start_trace(request_id=f"test-{i}")
            record_agent_call("extractor", 100.0 + i * 10, tokens_in=100, tokens_out=50, cost_usd=0.001)
            end_trace()

        summary = get_metrics_summary()
        assert summary["total_requests"] == 3
        assert summary["total_tokens_in"] == 300
        assert summary["total_tokens_out"] == 150
        assert summary["total_cost_usd"] > 0
