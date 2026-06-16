from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


PRACTICE_MODES = ("Learn", "Practice", "Timed Mock", "Review")


def validate_self_rating(value: Any) -> int:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return 0
    if rating < 1 or rating > 5:
        return 0
    return rating


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y", "да"}
    return bool(value)


def normalize_algorithm_attempt(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": str(raw.get("timestamp") or datetime.now(timezone.utc).isoformat()),
        "lesson_id": str(raw.get("lesson_id") or "").strip(),
        "mode": str(raw.get("mode") or "Practice").strip(),
        "tests_passed": normalize_bool(raw.get("tests_passed")),
        "time_spent_minutes": max(0, int(raw.get("time_spent_minutes") or 0)),
        "big_o_explanation": str(raw.get("big_o_explanation") or "").strip(),
        "edge_cases": str(raw.get("edge_cases") or "").strip(),
        "what_was_hard": str(raw.get("what_was_hard") or "").strip(),
        "retry_later": normalize_bool(raw.get("retry_later")),
    }


def normalize_interview_answer_attempt(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": str(raw.get("timestamp") or datetime.now(timezone.utc).isoformat()),
        "question_id": str(raw.get("question_id") or "").strip(),
        "company": str(raw.get("company") or "").strip(),
        "question": str(raw.get("question") or "").strip(),
        "answer_notes": str(raw.get("answer_notes") or "").strip(),
        "self_rating": validate_self_rating(raw.get("self_rating")),
        "repeat_later": normalize_bool(raw.get("repeat_later")),
    }


def summarize_interview_arena_progress(
    algorithm_attempts: dict[str, list[dict[str, Any]]] | None,
    interview_attempts: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, int]:
    algo_attempt_lists = algorithm_attempts if isinstance(algorithm_attempts, dict) else {}
    interview_attempt_lists = interview_attempts if isinstance(interview_attempts, dict) else {}
    algorithm_attempt_count = sum(len(value) for value in algo_attempt_lists.values() if isinstance(value, list))
    mock_sessions_completed = sum(
        1
        for attempts in algo_attempt_lists.values()
        if isinstance(attempts, list)
        for attempt in attempts
        if isinstance(attempt, dict) and attempt.get("mode") == "Timed Mock"
    )
    repeat_later_count = sum(
        1
        for attempts in interview_attempt_lists.values()
        if isinstance(attempts, list)
        for attempt in attempts
        if isinstance(attempt, dict) and attempt.get("repeat_later") is True
    )
    interview_answer_count = sum(len(value) for value in interview_attempt_lists.values() if isinstance(value, list))
    return {
        "algorithm_attempts": algorithm_attempt_count,
        "mock_sessions_completed": mock_sessions_completed,
        "interview_answers": interview_answer_count,
        "questions_repeat_later": repeat_later_count,
    }


def extract_expected_complexity(text: str) -> str:
    matches = re.findall(r"O\([^)]+\)(?:\s*time|\s*space)?", text or "", flags=re.I)
    if not matches:
        return "Not specified"
    seen: list[str] = []
    for match in matches:
        cleaned = match.strip()
        if cleaned not in seen:
            seen.append(cleaned)
    return " · ".join(seen[:4])


def infer_difficulty(text: str) -> str:
    lowered = (text or "").casefold()
    for difficulty in ("easy", "medium", "hard"):
        if difficulty in lowered:
            return difficulty.capitalize()
    return "Not specified"
