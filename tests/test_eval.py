"""Tests for the evaluation harness."""

from notifai.core.schemas import CollegeEvent
from notifai.eval.dataset import EVAL_CASES
from notifai.eval.metrics import (
    aggregate_metrics,
    compute_case_metrics,
    compute_field_accuracy,
    compute_hallucination_rate,
    compute_precision_recall,
)
from notifai.eval.runner import format_eval_report, run_eval


class TestDataset:
    def test_dataset_size(self) -> None:
        assert len(EVAL_CASES) >= 50

    def test_all_cases_have_required_fields(self) -> None:
        for case in EVAL_CASES:
            assert "message" in case
            assert "category" in case
            assert "expected" in case
            assert isinstance(case["expected"], list)

    def test_categories(self) -> None:
        categories = {c["category"] for c in EVAL_CASES}
        assert "simple_english" in categories
        assert "hinglish" in categories
        assert "ambiguous_dates" in categories
        assert "multi_event" in categories
        assert "cancellation" in categories
        assert "chatter" in categories
        assert "deadlines" in categories
        assert "mixed" in categories


class TestMetrics:
    def test_field_accuracy_perfect(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Team Meeting",
                date="2026-11-19",
                time="10:00",
                description="Team meeting in Room B",
            )
        ]
        expected = [
            {
                "title": "Team Meeting",
                "date": "2026-11-19",
                "time": "10:00",
                "description": "Team meeting in Room B",
                "notice_type": "meeting",
                "is_important_notice": True,
            }
        ]
        acc = compute_field_accuracy(events, expected)
        assert acc["title"] == 1.0
        assert acc["date"] == 1.0
        assert acc["time"] == 1.0

    def test_precision_recall_perfect(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Meeting",
                date="2026-11-19",
                time="10:00",
                description="Sync",
            )
        ]
        expected = [
            {
                "title": "Meeting",
                "date": "2026-11-19",
                "time": "10:00",
                "description": "Sync",
                "notice_type": "meeting",
                "is_important_notice": True,
            }
        ]
        pr = compute_precision_recall(events, expected)
        assert pr["precision"] == 1.0
        assert pr["recall"] == 1.0
        assert pr["f1"] == 1.0

    def test_precision_recall_empty_expected(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Meeting",
                date="2026-11-19",
                time="10:00",
                description="Sync",
            )
        ]
        pr = compute_precision_recall(events, [])
        assert pr["precision"] == 0.0
        assert pr["recall"] == 1.0

    def test_precision_recall_no_extraction(self) -> None:
        expected = [
            {
                "title": "Meeting",
                "date": "2026-11-19",
                "time": "10:00",
                "description": "Sync",
                "notice_type": "meeting",
                "is_important_notice": True,
            }
        ]
        pr = compute_precision_recall([], expected)
        assert pr["precision"] == 0.0
        assert pr["recall"] == 0.0

    def test_hallucination_rate(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Meeting",
                date="2026-11-19",
                time="10:00",
                description="Sync",
            ),
            CollegeEvent(
                is_important_notice=True,
                title="Fake Event",
                date="2026-11-20",
                time="11:00",
                description="Not in source",
            ),
        ]
        expected = [
            {
                "title": "Meeting",
                "date": "2026-11-19",
                "time": "10:00",
                "description": "Sync",
                "notice_type": "meeting",
                "is_important_notice": True,
            }
        ]
        rate = compute_hallucination_rate(events, expected)
        assert rate == 0.5

    def test_case_metrics(self) -> None:
        events = [
            CollegeEvent(
                is_important_notice=True,
                title="Meeting",
                date="2026-11-19",
                time="10:00",
                description="Team sync",
            )
        ]
        expected = [
            {
                "title": "Meeting",
                "date": "2026-11-19",
                "time": "10:00",
                "description": "Team sync",
                "notice_type": "meeting",
                "is_important_notice": True,
            }
        ]
        m = compute_case_metrics(events, expected, latency_ms=150.0, cost_usd=0.001)
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["latency_ms"] == 150.0
        assert m["cost_usd"] == 0.001


class TestEvalRunner:
    def test_mock_eval(self) -> None:
        results = run_eval(mock=True)
        overall = results["overall"]
        assert overall["total_cases"] >= 50
        assert overall["avg_f1"] == 1.0
        assert overall["avg_hallucination_rate"] == 0.0

    def test_mock_eval_report(self) -> None:
        results = run_eval(mock=True)
        report = format_eval_report(results)
        assert "NotifAI Evaluation Report" in report
        assert "Total Cases:" in report
        assert "Precision:" in report

    def test_mock_eval_with_categories(self) -> None:
        results = run_eval(mock=True)
        report = format_eval_report(results, show_categories=True)
        assert "Per-Category Breakdown" in report

    def test_mock_eval_json_serializable(self) -> None:
        import json

        results = run_eval(mock=True)
        json_str = json.dumps(results, default=str)
        assert len(json_str) > 100