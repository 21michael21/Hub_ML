from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.projects.models import normalize_project_recipe


def load_project_recipe(path: str | Path) -> dict[str, Any] | None:
    recipe_path = Path(path)
    try:
        data = json.loads(recipe_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return normalize_project_recipe(data)


def load_project_recipes(projects_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(projects_dir)
    if not root.exists() or not root.is_dir():
        return []

    projects: list[dict[str, Any]] = []
    for recipe_path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
        project = load_project_recipe(recipe_path)
        if project is not None:
            project["source_path"] = str(recipe_path)
            projects.append(project)

    projects.sort(key=lambda item: (str(item.get("track", "")).casefold(), str(item.get("title", "")).casefold()))
    return projects


def load_project_recipes_from_dirs(project_dirs: list[str | Path] | tuple[str | Path, ...]) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    for projects_dir in project_dirs:
        projects.extend(load_project_recipes(projects_dir))
    projects.sort(key=lambda item: (str(item.get("track", "")).casefold(), str(item.get("title", "")).casefold()))
    return projects
