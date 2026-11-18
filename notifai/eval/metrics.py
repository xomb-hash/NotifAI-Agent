"""Evaluation metrics: field accuracy, precision/recall, hallucination rate."""

from __future__ import annotations

import re
from typing import Any

from notifai.core.schemas import CollegeEvent


def _normalize(text: str) -> str:
    """Normalize text for comparison (lowercase, strip, collapse whitespace)."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _date_match(actual: str, expected: str) -> bool:
    """Check if two dates match (exact match required)."""
    return actual.strip() == expected.strip()


def _time_match(actual: str, expected: str) -> bool:
    """Check if two times match (exact match required)."""
    return actual.strip() == expected.strip()


def _title_match(actual: str, expected: str) -> bool:
    """Check if titles match (normalized, substring-tolerant)."""
    a = _normalize(actual)
    e = _normalize(expected)
    if a == e:
        return True
    if e in a or a in e:
        return True
    words_a = set(a.split())
    words_e = set(e.split())
    overlap = words_a & words_e
    return len(overlap) / max(len(words_e), 1) >= 0.5


def compute_field_accuracy(
    extracted: list[CollegeEvent],
    expected: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute field-level accuracy for extracted events.

    Returns dict with per-field accuracy rates.
    """
    if not expected:
        return {"title": 0.0, "date": 0.0, "time": 0.0, "description": 0.0}

    total = len(expected)
    correct = {"title": 0, "date": 0, "time": 0, "description": 0}

    for exp in expected:
        best_match: CollegeEvent | None = None
        best_score = 0.0

        for ext in extracted:
            score = 0.0
            if _title_match(ext.title, exp["title"]):
                score += 0.4
            if _date_match(ext.date, exp["date"]):
                score += 0.3
            if _time_match(ext.time, exp["time"]):
                score += 0.2
            if _normalize(ext.description) and _normalize(exp["description"]):
                if (
                    _normalize(exp["description"]) in _normalize(ext.description)
                    or _normalize(ext.description) in _normalize(exp["description"])
                ):
                    score += 0.1
            if score > best_score:
                best_score = score
                best_match = ext

        if best_match:
            if _title_match(best_match.title, exp["title"]):
                correct["title"] += 1
            if _date_match(best_match.date, exp["date"]):
                correct["date"] += 1
            if _time_match(best_match.time, exp["time"]):
                correct["time"] += 1
            if _normalize(exp["description"]) and _normalize(best_match.description):
                if (
                    _normalize(exp["description"]) in _normalize(best_match.description)
                    or _normalize(best_match.description) in _normalize(exp["description"])
                ):
                    correct["description"] += 1

    return {
        field: round(correct[field] / total, 4) if total > 0 else 0.0
        for field in correct
    }


def compute_precision_recall(
    extracted: list[CollegeEvent],
    expected: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute event-level precision and recall.

    An event is a true positive if its title and date match an expected event.
    """
    if not expected and not extracted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    if not expected:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}

    if not extracted:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    matched_expected: set[int] = set()
    matched_extracted: set[int] = set()

    for i, ext in enumerate(extracted):
        for j, exp in enumerate(expected):
            if j in matched_expected:
                continue
            if _title_match(ext.title, exp["title"]) and _date_match(ext.date, exp["date"]):
                matched_expected.add(j)
                matched_extracted.add(i)
                break

    tp = len(matched_extracted)
    fp = len(extracted) - tp
    fn = len(expected) - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def compute_hallucination_rate(
    extracted: list[CollegeEvent],
    expected: list[dict[str, Any]],
) -> float:
    """Compute hallucination rate: fraction of extracted events not in expected."""
    if not extracted:
        return 0.0

    hallucinated = 0
    for ext in extracted:
        matched = False
        for exp in expected:
            if _title_match(ext.title, exp["title"]):
                matched = True
                break
        if not matched:
            hallucinated += 1

    return round(hallucinated / len(extracted), 4)


def compute_case_metrics(
    extracted: list[CollegeEvent],
    expected: list[dict[str, Any]],
    latency_ms: float,
    cost_usd: float,
) -> dict[str, Any]:
    """Compute all metrics for a single eval case."""
    field_acc = compute_field_accuracy(extracted, expected)
    pr = compute_precision_recall(extracted, expected)
    hall_rate = compute_hallucination_rate(extracted, expected)

    return {
        "expected_count": len(expected),
        "extracted_count": len(extracted),
        "field_accuracy": field_acc,
        "precision": pr["precision"],
        "recall": pr["recall"],
        "f1": pr["f1"],
        "hallucination_rate": hall_rate,
        "latency_ms": round(latency_ms, 2),
        "cost_usd": round(cost_usd, 6),
    }


def aggregate_metrics(
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate metrics across all eval cases."""
    total = len(case_results)
    if total == 0:
        return {}

    avg_field_acc = {
        field: round(
            sum(
                cr["field_accuracy"][field]
                for cr in case_results
                if "field_accuracy" in cr
            )
            / total,
            4,
        )
        for field in ["title", "date", "time", "description"]
    }

    avg_precision = round(
        sum(cr.get("precision", 0) for cr in case_results) / total, 4
    )
    avg_recall = round(
        sum(cr.get("recall", 0) for cr in case_results) / total, 4
    )
    avg_f1 = round(
        sum(cr.get("f1", 0) for cr in case_results) / total, 4
    )
    avg_hallucination = round(
        sum(cr.get("hallucination_rate", 0) for cr in case_results) / total, 4
    )

    latencies = [cr["latency_ms"] for cr in case_results if "latency_ms" in cr]
    latencies_sorted = sorted(latencies)
    p50 = _percentile(latencies_sorted, 50)
    p95 = _percentile(latencies_sorted, 95)
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    avg_cost = round(
        sum(cr.get("cost_usd", 0) for cr in case_results) / total, 6
    )
    total_cost = round(
        sum(cr.get("cost_usd", 0) for cr in case_results), 6
    )

    total_expected = sum(cr.get("expected_count", 0) for cr in case_results)
    total_extracted = sum(cr.get("extracted_count", 0) for cr in case_results)

    return {
        "total_cases": total,
        "total_expected_events": total_expected,
        "total_extracted_events": total_extracted,
        "avg_field_accuracy": avg_field_acc,
        "avg_precision": avg_precision,
        "avg_recall": avg_recall,
        "avg_f1": avg_f1,
        "avg_hallucination_rate": avg_hallucination,
        "avg_latency_ms": avg_latency,
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "avg_cost_per_request_usd": avg_cost,
        "total_cost_usd": total_cost,
    }


def group_by_category(
    case_results: list[dict[str, Any]],
    cases: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Group metrics by eval category."""
    categories: dict[str, list[dict[str, Any]]] = {}
    for i, cr in enumerate(case_results):
        cat = cases[i].get("category", "unknown")
        categories.setdefault(cat, []).append(cr)

    return {
        cat: aggregate_metrics(results)
        for cat, results in categories.items()
    }


def _percentile(sorted_data: list[float], percentile: int) -> float:
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    if f == c:
        return sorted_data[f]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)