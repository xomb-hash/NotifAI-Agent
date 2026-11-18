"""Per-request tracing and LLM metrics tracking."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RequestTrace:
    """Trace data for a single request through the multi-agent pipeline."""

    request_id: str = ""
    session_id: str = ""
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float = 0.0
    agents: list[dict[str, Any]] = field(default_factory=list)
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    retries: int = 0
    validation_failures: int = 0
    events_extracted: int = 0
    events_scheduled: int = 0
    errors: list[str] = field(default_factory=list)

    def record_agent(
        self,
        name: str,
        latency_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        success: bool = True,
        error: str = "",
    ) -> None:
        self.agents.append(
            {
                "name": name,
                "latency_ms": round(latency_ms, 2),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "success": success,
                "error": error,
            }
        )
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        self.total_cost_usd += cost_usd
        if not success:
            self.errors.append(f"{name}: {error}")

    def finish(self) -> dict[str, Any]:
        self.end_time = time.perf_counter()
        total_latency_ms = (self.end_time - self.start_time) * 1000
        tokens_per_sec = (
            (self.total_tokens_in + self.total_tokens_out) / (total_latency_ms / 1000)
            if total_latency_ms > 0
            else 0.0
        )

        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "total_latency_ms": round(total_latency_ms, 2),
            "agents": self.agents,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_tokens": self.total_tokens_in + self.total_tokens_out,
            "tokens_per_sec": round(tokens_per_sec, 2),
            "total_cost_usd": round(self.total_cost_usd, 6),
            "retries": self.retries,
            "validation_failures": self.validation_failures,
            "events_extracted": self.events_extracted,
            "events_scheduled": self.events_scheduled,
            "errors": self.errors,
        }


_traces: list[RequestTrace] = []
_active_trace: RequestTrace | None = None


def start_trace(request_id: str = "", session_id: str = "") -> RequestTrace:
    global _active_trace
    _active_trace = RequestTrace(request_id=request_id, session_id=session_id)
    return _active_trace


def get_active_trace() -> RequestTrace | None:
    return _active_trace


def end_trace() -> dict[str, Any] | None:
    global _active_trace
    if _active_trace is None:
        return None
    result = _active_trace.finish()
    _traces.append(_active_trace)
    _active_trace = None
    return result


def record_agent_call(
    name: str,
    latency_ms: float,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    success: bool = True,
    error: str = "",
) -> None:
    if _active_trace is not None:
        _active_trace.record_agent(
            name=name,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            success=success,
            error=error,
        )


def get_metrics_summary() -> dict[str, Any]:
    """Aggregate metrics across all traces."""
    if not _traces:
        return {
            "total_requests": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_retries": 0,
            "total_validation_failures": 0,
        }

    latencies = [
        (t.end_time - t.start_time) * 1000
        for t in _traces
        if t.end_time > t.start_time
    ]
    latencies_sorted = sorted(latencies)

    p50 = _percentile(latencies_sorted, 50) if latencies_sorted else 0.0
    p95 = _percentile(latencies_sorted, 95) if latencies_sorted else 0.0

    return {
        "total_requests": len(_traces),
        "total_cost_usd": round(sum(t.total_cost_usd for t in _traces), 6),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "total_tokens_in": sum(t.total_tokens_in for t in _traces),
        "total_tokens_out": sum(t.total_tokens_out for t in _traces),
        "total_retries": sum(t.retries for t in _traces),
        "total_validation_failures": sum(t.validation_failures for t in _traces),
        "total_events_extracted": sum(t.events_extracted for t in _traces),
        "total_events_scheduled": sum(t.events_scheduled for t in _traces),
    }


def get_recent_traces(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent traces as dicts."""
    return [
        {
            "request_id": t.request_id,
            "session_id": t.session_id,
            "latency_ms": round((t.end_time - t.start_time) * 1000, 2) if t.end_time > t.start_time else 0,
            "cost_usd": round(t.total_cost_usd, 6),
            "events_extracted": t.events_extracted,
            "events_scheduled": t.events_scheduled,
            "retries": t.retries,
            "errors": t.errors,
        }
        for t in _traces[-limit:]
    ]


def reset_traces() -> None:
    global _traces
    _traces = []


def _percentile(sorted_data: list[float], percentile: int) -> float:
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    if f == c:
        return sorted_data[f]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)