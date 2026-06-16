from __future__ import annotations

import re
from pathlib import Path
from typing import Any


MENTOR_DATASET_FILES = ("df_events.csv", "df_matching.csv", "df_orders.csv")


def humanize_notebook_name(name: str) -> str:
    stem = Path(str(name)).stem
    replacements = {
        "analysis_1_stats": "Stats",
        "analysis_2_numpy": "NumPy",
        "analysis_3_pandas": "Pandas",
        "python_1_start": "Python Start",
        "python_2_basics": "Python Basics",
        "python_2_project": "Python Project",
        "python_3_architecture": "Python Architecture",
        "python_4_advanced": "Advanced Python",
        "python_5_OOP": "Python OOP",
        "python_6_advanced+": "Very Advanced Python",
        "python_EXTRA_typing": "Python Typing",
    }
    if stem in replacements:
        return replacements[stem]
    words = re.split(r"[_\-\s]+", stem)
    return " ".join(word.capitalize() for word in words if word)


def line_has_starter_stub(line: str) -> bool:
    return bool(re.search(r"#\s*TODO|#\s*(?:ваш|ВАШ)\s+код|\.\.\.|\bpass\b|NotImplementedError", line, re.I))


def extract_mentor_task_test_code(starter_code: str) -> str:
    lines = starter_code.splitlines()
    assert_indexes = [index for index, line in enumerate(lines) if line.strip().startswith("assert ")]
    if not assert_indexes:
        return ""

    first_assert = assert_indexes[0]
    start = first_assert
    index = first_assert - 1
    while index >= 0:
        line = lines[index]
        if not line.strip() or line_has_starter_stub(line):
            break
        start = index
        index -= 1

    return "\n".join(lines[start:]).strip()


def extract_mentor_task_check_code(starter_code: str) -> str:
    return extract_mentor_task_test_code(starter_code)


def extract_mentor_task_solution_code(starter_code: str, test_code: str) -> str:
    starter = str(starter_code or "").rstrip()
    tests = str(test_code or "").strip()
    if tests and starter.endswith(tests):
        starter = starter[: -len(tests)].rstrip()

    solution_lines = [
        line
        for line in starter.splitlines()
        if not line.strip().startswith("assert ")
    ]
    solution = "\n".join(solution_lines).strip()
    return solution or "# Напишите решение здесь.\n"


def code_assigns_name(code: str, name: str) -> bool:
    return bool(re.search(rf"(^|\n)\s*{re.escape(name)}\s*=", str(code or "")))


def task_context_text(task: dict[str, Any]) -> str:
    parts = [
        task.get("title", ""),
        task.get("prompt", ""),
        task.get("starter_code", ""),
        task.get("solution_starter", ""),
        task.get("test_code", ""),
    ]
    return "\n".join(str(part or "") for part in parts)


def detect_task_datasets(task: dict[str, Any]) -> list[str]:
    context = task_context_text(task).casefold()
    found: list[str] = []
    for dataset_name in MENTOR_DATASET_FILES:
        stem = Path(dataset_name).stem.casefold()
        variable_aliases = {
            "df_events.csv": ("df_events_task",),
            "df_matching.csv": ("matching",),
            "df_orders.csv": (),
        }.get(dataset_name, ())
        if (
            dataset_name.casefold() in context
            or re.search(rf"\b{re.escape(stem)}\b", context)
            or any(re.search(rf"\b{re.escape(alias)}\b", context) for alias in variable_aliases)
        ):
            found.append(dataset_name)
    return found


def dataset_snippet_for_task(task: dict[str, Any]) -> str:
    lines: list[str] = []
    datasets = task.get("datasets") or detect_task_datasets(task)
    for dataset_name in datasets:
        variable_name = Path(str(dataset_name)).stem
        lines.append(f'{variable_name} = pd.read_csv("datasets/{dataset_name}")')
    if not lines:
        return ""
    return "import pandas as pd\n" + "\n".join(lines)


def infer_mentor_task_setup_code(task: dict[str, Any]) -> str:
    context = task_context_text(task)
    solution = str(task.get("solution_starter") or "")
    setup: list[str] = []

    if "df_events_task" in context and not code_assigns_name(solution, "df_events_task"):
        setup.append('df_events_task = pd.read_csv("datasets/df_events.csv")')

    if "screen_views_late" in context and not code_assigns_name(solution, "screen_views_late"):
        if not any(line.startswith("df_events_task =") for line in setup):
            setup.append('df_events_task = pd.read_csv("datasets/df_events.csv")')
        setup.append(
            'screen_views_late = df_events_task[(df_events_task["event_type"] == "item.added") '
            '& (df_events_task["event_date"] > "2025-02-10")]'
        )

    if re.search(r"\bmatching\b|\bdf_matching\b", context) and not (
        code_assigns_name(solution, "matching") or code_assigns_name(solution, "df_matching")
    ):
        setup.append('matching = pd.read_csv("datasets/df_matching.csv")')

    if not setup:
        return ""
    return "import pandas as pd\n" + "\n".join(setup)


def mentor_task_dependency_hint(task: dict[str, Any]) -> str:
    setup_code = str(task.get("setup_code") or "")
    if not setup_code:
        return ""
    names: list[str] = []
    for name in ("df_events_task", "screen_views_late", "matching"):
        if code_assigns_name(setup_code, name):
            names.append(name)
    if not names:
        return ""
    return (
        "Эта задача похожа на зависимую от предыдущих pandas-шагов. "
        f"Перед проверкой приложение добавит setup для: {', '.join(names)}."
    )


def normalize_mentor_task(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("has_asserts") is not True:
        return None

    task_id = str(raw.get("id") or "").strip()
    source_notebook = str(raw.get("source_notebook") or "").strip()
    title = str(raw.get("title") or "").strip()
    prompt = str(raw.get("prompt") or "").strip()
    starter_code = str(raw.get("starter_code") or "").strip()
    confidence = str(raw.get("confidence") or "").strip().casefold()
    tests = [str(item).strip() for item in raw.get("tests", []) if str(item).strip()]

    if not task_id or not source_notebook or not prompt or not starter_code or not tests:
        return None
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    test_code = extract_mentor_task_test_code(starter_code) or "\n".join(tests)
    solution_starter = extract_mentor_task_solution_code(starter_code, test_code)
    task = {
        "id": task_id,
        "source_notebook": source_notebook,
        "notebook_label": humanize_notebook_name(source_notebook),
        "title": title or task_id,
        "prompt": prompt,
        "starter_code": starter_code,
        "solution_starter": solution_starter,
        "tests": tests,
        "test_code": test_code,
        "check_code": test_code,
        "confidence": confidence,
        "code_cell_index": raw.get("code_cell_index"),
        "prompt_cell_index": raw.get("prompt_cell_index"),
    }
    task["setup_code"] = infer_mentor_task_setup_code(task)
    task["datasets"] = detect_task_datasets(task)
    task["dependency_hint"] = mentor_task_dependency_hint(task)
    return task
