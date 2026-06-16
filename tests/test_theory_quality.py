from pathlib import Path

from core.reports.theory_quality import (
    coverage_by_track,
    load_json_report,
    missing_required_topics,
    report_list,
    theory_summary,
    weakest_notes,
)


def test_load_json_report_handles_missing_and_invalid(tmp_path: Path) -> None:
    assert load_json_report(tmp_path / "missing.json") == {}

    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")

    assert load_json_report(bad) == {}


def test_theory_report_helpers_sort_notes_when_summary_has_no_weakest() -> None:
    report = {
        "summary": {
            "total_notes": 2,
            "notes_without_examples": ["a.md", "b.md"],
        },
        "notes": [
            {"relative_path": "strong.md", "quality_score": 80, "word_count": 300},
            {"relative_path": "weak.md", "quality_score": 10, "word_count": 20},
        ],
    }

    assert theory_summary(report)["total_notes"] == 2
    assert report_list(theory_summary(report), "notes_without_examples") == ["a.md", "b.md"]
    assert weakest_notes(report, limit=1)[0]["relative_path"] == "weak.md"


def test_coverage_report_helpers() -> None:
    report = {
        "summary": {
            "missing_required_topics": [
                {"id": "sql.join", "title": "SQL Joins", "status": "missing"}
            ],
            "coverage_by_track": {
                "SQL": {"covered": 1, "missing": 1},
                "Broken": "ignored",
            },
        }
    }

    assert missing_required_topics(report)[0]["id"] == "sql.join"
    assert coverage_by_track(report) == {"SQL": {"covered": 1, "missing": 1}}
