"""Evaluation runner: runs the full pipeline against the labeled dataset.

Usage:
    python -m notifai.eval.runner              # full pipeline
    python -m notifai.eval.runner --mock       # mock mode (CI, no API key)
    python -m notifai.eval.runner --json       # JSON output
    python -m notifai.eval.runner --category   # per-category breakdown
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from notifai.eval.dataset import EVAL_CASES
from notifai.eval.metrics import aggregate_metrics, compute_case_metrics, group_by_category


def _run_case_mock(case: dict[str, Any]) -> dict[str, Any]:
    """Run a case in mock mode (returns expected events as extracted)."""
    from notifai.core.schemas import CollegeEvent

    events = [
        CollegeEvent(
            is_important_notice=e["is_important_notice"],
            title=e["title"],
            date=e["date"],
            time=e["time"],
            description=e["description"],
            notice_type=e["notice_type"],
        )
        for e in case["expected"]
    ]

    return {
        "case_index": EVAL_CASES.index(case),
        "category": case.get("category", "unknown"),
        "message": case["message"][:100],
        "extracted": events,
        "latency_ms": 0.0,
        "cost_usd": 0.0,
        "success": True,
    }


def _run_case_real(case: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
    """Run a case through the real multi-agent pipeline."""
    from notifai.agents.router import route_message

    t0 = time.perf_counter()
    try:
        result = route_message(
            message=case["message"],
            enable_rag=False,
            enable_validation=True,
            dry_run=dry_run,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        cost = 0.0
        if result.extraction:
            cost = result.extraction.cost_usd
        if result.validation:
            cost += result.validation.validation_cost_usd

        return {
            "case_index": EVAL_CASES.index(case),
            "category": case.get("category", "unknown"),
            "message": case["message"][:100],
            "extracted": result.final_events,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "success": True,
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "case_index": EVAL_CASES.index(case),
            "category": case.get("category", "unknown"),
            "message": case["message"][:100],
            "extracted": [],
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
            "success": False,
            "error": str(e),
        }


def run_eval(mock: bool = False) -> dict[str, Any]:
    """Run the full evaluation."""
    case_results: list[dict[str, Any]] = []

    for case in EVAL_CASES:
        if mock:
            result = _run_case_mock(case)
        else:
            result = _run_case_real(case)

        metrics = compute_case_metrics(
            extracted=result["extracted"],
            expected=case["expected"],
            latency_ms=result["latency_ms"],
            cost_usd=result["cost_usd"],
        )
        result["metrics"] = metrics
        case_results.append(result)

    overall = aggregate_metrics([cr["metrics"] for cr in case_results])
    by_category = group_by_category([cr["metrics"] for cr in case_results], EVAL_CASES)

    return {
        "overall": overall,
        "by_category": by_category,
        "case_results": [
            {
                "case_index": cr["case_index"],
                "category": cr["category"],
                "message": cr["message"],
                "success": cr["success"],
                "metrics": cr["metrics"],
            }
            for cr in case_results
        ],
    }


def format_eval_report(results: dict[str, Any], show_categories: bool = False) -> str:
    """Format eval results as a human-readable report."""
    overall = results["overall"]
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("  NotifAI Evaluation Report")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Total Cases:              {overall.get('total_cases', 0)}")
    lines.append(f"  Total Expected Events:    {overall.get('total_expected_events', 0)}")
    lines.append(f"  Total Extracted Events:   {overall.get('total_extracted_events', 0)}")
    lines.append("")
    lines.append("  Field Accuracy:")
    for field, val in overall.get("avg_field_accuracy", {}).items():
        lines.append(f"    {field:15s}  {val:.2%}")
    lines.append("")
    lines.append(f"  Precision:                {overall.get('avg_precision', 0):.2%}")
    lines.append(f"  Recall:                   {overall.get('avg_recall', 0):.2%}")
    lines.append(f"  F1 Score:                 {overall.get('avg_f1', 0):.2%}")
    lines.append(f"  Hallucination Rate:       {overall.get('avg_hallucination_rate', 0):.2%}")
    lines.append("")
    lines.append(f"  Avg Latency:              {overall.get('avg_latency_ms', 0):.2f} ms")
    lines.append(f"  p50 Latency:              {overall.get('p50_latency_ms', 0):.2f} ms")
    lines.append(f"  p95 Latency:              {overall.get('p95_latency_ms', 0):.2f} ms")
    lines.append("")
    lines.append(f"  Avg Cost / Request:       ${overall.get('avg_cost_per_request_usd', 0):.6f}")
    lines.append(f"  Total Cost:               ${overall.get('total_cost_usd', 0):.6f}")
    lines.append("")

    if show_categories:
        lines.append("-" * 70)
        lines.append("  Per-Category Breakdown:")
        lines.append("-" * 70)
        for cat, cat_metrics in results.get("by_category", {}).items():
            lines.append(f"  [{cat}]")
            lines.append(f"    Cases:       {cat_metrics.get('total_cases', 0)}")
            lines.append(f"    Precision:   {cat_metrics.get('avg_precision', 0):.2%}")
            lines.append(f"    Recall:      {cat_metrics.get('avg_recall', 0):.2%}")
            lines.append(f"    F1:          {cat_metrics.get('avg_f1', 0):.2%}")
            lines.append(f"    Hallucination: {cat_metrics.get('avg_hallucination_rate', 0):.2%}")
            lines.append(f"    Avg Latency: {cat_metrics.get('avg_latency_ms', 0):.2f} ms")
            lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="NotifAI Evaluation Runner")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no API key)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--category", action="store_true", help="Show per-category breakdown")
    args = parser.parse_args()

    results = run_eval(mock=args.mock)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_eval_report(results, show_categories=args.category))


if __name__ == "__main__":
    main()