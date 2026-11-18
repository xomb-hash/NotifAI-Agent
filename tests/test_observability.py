"""Tests for observability and reporting."""

from notifai.observability.report import format_report
from notifai.observability.tracing import (
    end_trace,
    get_metrics_summary,
    get_recent_traces,
    record_agent_call,
    reset_traces,
    start_trace,
)


class TestTracing:
    def test_trace_lifecycle(self) -> None:
        reset_traces()
        start_trace(request_id="r1", session_id="s1")
        record_agent_call("extractor", 100.0, tokens_in=100, tokens_out=50, cost_usd=0.001)
        record_agent_call("validator", 50.0, success=True)
        result = end_trace()

        assert result is not None
        assert result["request_id"] == "r1"
        assert result["total_tokens_in"] == 100
        assert result["total_tokens_out"] == 50
        assert len(result["agents"]) == 2

    def test_metrics_summary_empty(self) -> None:
        reset_traces()
        summary = get_metrics_summary()
        assert summary["total_requests"] == 0
        assert summary["total_cost_usd"] == 0.0

    def test_metrics_summary_with_traces(self) -> None:
        reset_traces()
        for i in range(5):
            start_trace(request_id=f"test-{i}")
            record_agent_call(
                "extractor",
                100.0 + i * 10,
                tokens_in=100,
                tokens_out=50,
                cost_usd=0.001,
            )
            end_trace()

        summary = get_metrics_summary()
        assert summary["total_requests"] == 5
        assert summary["total_tokens_in"] == 500
        assert summary["total_tokens_out"] == 250
        assert summary["total_cost_usd"] > 0
        assert summary["p50_latency_ms"] >= 0
        assert summary["p95_latency_ms"] >= 0

    def test_recent_traces(self) -> None:
        reset_traces()
        for i in range(3):
            start_trace(request_id=f"trace-{i}")
            record_agent_call("test", 50.0)
            end_trace()

        traces = get_recent_traces(limit=2)
        assert len(traces) == 2

    def test_trace_with_errors(self) -> None:
        reset_traces()
        start_trace(request_id="err-1")
        record_agent_call("extractor", 100.0, success=False, error="API timeout")
        record_agent_call("validator", 50.0, success=True)
        result = end_trace()

        assert result is not None
        assert len(result["errors"]) == 1
        assert "extractor" in result["errors"][0]


class TestReport:
    def test_format_report_empty(self) -> None:
        reset_traces()
        summary = get_metrics_summary()
        report = format_report(summary, [])
        assert "NotifAI Observability Report" in report
        assert "Total Requests:" in report

    def test_format_report_with_traces(self) -> None:
        reset_traces()
        start_trace(request_id="r1")
        record_agent_call("extractor", 100.0, tokens_in=100, tokens_out=50, cost_usd=0.001)
        end_trace()

        summary = get_metrics_summary()
        traces = get_recent_traces(limit=5)
        report = format_report(summary, traces)
        assert "r1" in report[:12] or "r1" in report
        assert "Recent Traces" in report

    def test_format_report_with_errors(self) -> None:
        reset_traces()
        start_trace(request_id="err-report")
        record_agent_call("scheduler", 100.0, success=False, error="Calendar API down")
        end_trace()

        summary = get_metrics_summary()
        traces = get_recent_traces(limit=5)
        report = format_report(summary, traces)
        assert "ERROR" in report
        assert "Calendar API down" in report
