from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from core.tasks.models import normalize_mentor_task


@st.cache_data(show_spinner=False)
def load_mentor_tasks(path: str | Path) -> dict[str, Any]:
    mentor_tasks_path = Path(path)
    if not mentor_tasks_path.exists():
        return {"tasks": [], "skipped": 0}

    try:
        data = json.loads(mentor_tasks_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"tasks": [], "skipped": 0}

    raw_tasks = data.get("tasks", [])
    if not isinstance(raw_tasks, list):
        return {"tasks": [], "skipped": 0}

    tasks: list[dict[str, Any]] = []
    skipped = 0
    for raw in raw_tasks:
        task = normalize_mentor_task(raw)
        if task is None:
            skipped += 1
            continue
        tasks.append(task)

    tasks.sort(
        key=lambda task: (
            str(task["notebook_label"]).casefold(),
            {"high": 0, "medium": 1, "low": 2}.get(str(task["confidence"]), 9),
            str(task["title"]).casefold(),
        )
    )
    return {"tasks": tasks, "skipped": skipped}
