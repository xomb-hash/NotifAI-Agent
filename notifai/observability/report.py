"""CLI report tool for NotifAI observability metrics.

Usage:
    python -m notifai.observability.report           # summary
    python -m notifai.observability.report --json    # JSON output
    python -m notifai.observability.report --traces  # recent traces
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from notifai.observability.tracing import get_metrics_summary, get_recent_traces


def format_report(summary: dict[str, Any], traces: list[dict[str, Any]]) -> str:
    """Format metrics as a human-readable report."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  NotifAI Observability Report")
    lines.append("=" * 60)
    lines.append("")

    lines.append(f"  Total Requests:       {summary.get('total_requests', 0)}")
    lines.append(f"  Total Cost:           ${summary.get('total_cost_usd', 0):.6f}")
    lines.append(f"  Avg Latency:          {summary.get('avg_latency_ms', 0):.2f} ms")
    lines.append(f"  p50 Latency:          {summary.get('p50_latency_ms', 0):.2f} ms")
    lines.append(f"  p95 Latency:          {summary.get('p95_latency_ms', 0):.2f} ms")
    lines.append("")
    lines.append(f"  Tokens In:            {summary.get('total_tokens_in', 0):,}")
    lines.append(f"  Tokens Out:           {summary.get('total_tokens_out', 0):,}")
    lines.append(f"  Total Retries:        {summary.get('total_retries', 0)}")
    lines.append(f"  Validation Failures:  {summary.get('total_validation_failures', 0)}")
    lines.append(f"  Events Extracted:     {summary.get('total_events_extracted', 0)}")
    lines.append(f"  Events Scheduled:     {summary.get('total_events_scheduled', 0)}")
    lines.append("")

    if traces:
        lines.append("-" * 60)
        lines.append("  Recent Traces:")
        lines.append("-" * 60)
        for t in traces:
            status = "OK" if not t.get("errors") else "ERROR"
            lines.append(
                f"  [{status}] {t.get('request_id', 'N/A')[:12]}  "
                f"latency={t.get('latency_ms', 0):.0f}ms  "
                f"cost=${t.get('cost_usd', 0):.6f}  "
                f"events={t.get('events_extracted', 0)}/{t.get('events_scheduled', 0)}  "
                f"retries={t.get('retries', 0)}"
            )
            if t.get("errors"):
                for err in t["errors"]:
                    lines.append(f"       ERROR: {err}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="NotifAI Observability Report")
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    parser.add_argument(
        "--traces", action="store_true", help="Include recent traces"
    )
    args = parser.parse_args()

    summary = get_metrics_summary()
    traces = get_recent_traces(limit=10) if args.traces else []

    if args.json:
        output = {"summary": summary, "traces": traces} if traces else summary
        print(json.dumps(output, indent=2))
    else:
        print(format_report(summary, traces))


if __name__ == "__main__":
    main()
