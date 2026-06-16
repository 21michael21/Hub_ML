from core.interview_arena import (
    extract_expected_complexity,
    infer_difficulty,
    normalize_algorithm_attempt,
    normalize_interview_answer_attempt,
    summarize_interview_arena_progress,
    validate_self_rating,
)


def test_validate_self_rating() -> None:
    assert validate_self_rating(1) == 1
    assert validate_self_rating("5") == 5
    assert validate_self_rating(0) == 0
    assert validate_self_rating(6) == 0
    assert validate_self_rating("bad") == 0


def test_normalize_algorithm_attempt() -> None:
    attempt = normalize_algorithm_attempt(
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "lesson_id": "03_hashmap_pattern.py",
            "mode": "Timed Mock",
            "tests_passed": "yes",
            "time_spent_minutes": "20",
            "big_o_explanation": "O(n)",
            "edge_cases": "empty input",
            "what_was_hard": "remembering dict lookup",
            "retry_later": "true",
        }
    )

    assert attempt["tests_passed"] is True
    assert attempt["retry_later"] is True
    assert attempt["time_spent_minutes"] == 20


def test_normalize_interview_answer_attempt() -> None:
    attempt = normalize_interview_answer_attempt(
        {
            "question_id": "avito-0",
            "company": "Avito",
            "question": "What is precision?",
            "answer_notes": "TP / predicted positive",
            "self_rating": "4",
            "repeat_later": "yes",
        }
    )

    assert attempt["self_rating"] == 4
    assert attempt["repeat_later"] is True
    assert attempt["question_id"] == "avito-0"


def test_interview_arena_summary() -> None:
    summary = summarize_interview_arena_progress(
        {
            "a": [
                normalize_algorithm_attempt({"mode": "Timed Mock"}),
                normalize_algorithm_attempt({"mode": "Practice"}),
            ]
        },
        {
            "q1": [normalize_interview_answer_attempt({"repeat_later": True})],
            "q2": [normalize_interview_answer_attempt({"repeat_later": False})],
        },
    )

    assert summary == {
        "algorithm_attempts": 2,
        "mock_sessions_completed": 1,
        "interview_answers": 2,
        "questions_repeat_later": 1,
    }


def test_extract_complexity_and_difficulty() -> None:
    text = "Two Sum (Easy). Optimal: O(n) time, O(n) space. Brute force: O(n²) time."

    assert infer_difficulty(text) == "Easy"
    assert extract_expected_complexity(text) == "O(n) time · O(n) space · O(n²) time"
