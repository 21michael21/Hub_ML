from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_report(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return {}
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def theory_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    return summary if isinstance(summary, dict) else {}


def coverage_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    return summary if isinstance(summary, dict) else {}


def weakest_notes(report: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    summary = theory_summary(report)
    notes = summary.get("weakest_notes")
    if not isinstance(notes, list):
        notes = report.get("notes", [])
        if not isinstance(notes, list):
            return []
        notes = sorted(
            (note for note in notes if isinstance(note, dict)),
            key=lambda note: (
                int(note.get("quality_score") or 0),
                int(note.get("word_count") or 0),
                str(note.get("relative_path") or ""),
            ),
        )
    return [note for note in notes[:limit] if isinstance(note, dict)]


def report_list(summary: dict[str, Any], key: str, limit: int = 20) -> list[str]:
    value = summary.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:limit]]


def missing_required_topics(coverage_report: dict[str, Any]) -> list[dict[str, Any]]:
    summary = coverage_summary(coverage_report)
    topics = summary.get("missing_required_topics")
    if not isinstance(topics, list):
        return []
    return [topic for topic in topics if isinstance(topic, dict)]


def coverage_by_track(coverage_report: dict[str, Any]) -> dict[str, dict[str, int]]:
    summary = coverage_summary(coverage_report)
    raw = summary.get("coverage_by_track")
    if not isinstance(raw, dict):
        return {}

    result: dict[str, dict[str, int]] = {}
    for track, counts in raw.items():
        if not isinstance(counts, dict):
            continue
        result[str(track)] = {
            str(status): int(count)
            for status, count in counts.items()
            if isinstance(count, int)
        }
    return result

