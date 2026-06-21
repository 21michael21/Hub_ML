from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_INTERNAL_TARGET_KINDS = {
    "theory_note",
    "task",
    "project",
    "milestone",
    "practice",
    "dataset",
    "report",
}


@dataclass(frozen=True)
class InternalTarget:
    kind: str
    label: str
    target_id: str = ""
    path: str = ""
    project_id: str = ""
    milestone_id: str = ""
    source: str = ""


@dataclass(frozen=True)
class InternalTargetResult:
    target: InternalTarget
    exists: bool
    reason: str = ""
    resolved: str = ""


@dataclass(frozen=True)
class InternalIndexes:
    theory_paths: set[str] = field(default_factory=set)
    task_ids: set[str] = field(default_factory=set)
    project_ids: set[str] = field(default_factory=set)
    milestone_ids: set[tuple[str, str]] = field(default_factory=set)
    practice_ids: set[str] = field(default_factory=set)
    dataset_names: set[str] = field(default_factory=set)
    report_paths: set[str] = field(default_factory=set)


def normalize_identifier(value: object) -> str:
    return str(value or "").strip().casefold()


def normalize_relative_path(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.casefold()


def normalize_report_path(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return Path(text).as_posix().casefold()


def build_internal_indexes(
    *,
    notes: list[dict[str, Any]] | None = None,
    tasks: list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | None = None,
    practice_cards: list[dict[str, Any]] | None = None,
    datasets: list[dict[str, Any]] | None = None,
    reports: list[str | Path] | None = None,
) -> InternalIndexes:
    theory_paths = {
        normalize_relative_path(note.get("relative_path") or note.get("path"))
        for note in notes or []
        if normalize_relative_path(note.get("relative_path") or note.get("path"))
    }
    task_ids = {
        normalize_identifier(task.get("id"))
        for task in tasks or []
        if normalize_identifier(task.get("id"))
    }
    project_ids: set[str] = set()
    milestone_ids: set[tuple[str, str]] = set()
    for project in projects or []:
        project_id = normalize_identifier(project.get("id"))
        if not project_id:
            continue
        project_ids.add(project_id)
        for milestone in project.get("milestones", []):
            if not isinstance(milestone, dict):
                continue
            milestone_id = normalize_identifier(milestone.get("id"))
            if milestone_id:
                milestone_ids.add((project_id, milestone_id))

    practice_ids = {
        normalize_identifier(card.get("id"))
        for card in practice_cards or []
        if normalize_identifier(card.get("id"))
    }
    dataset_names = {
        normalize_identifier(dataset.get("name"))
        for dataset in datasets or []
        if normalize_identifier(dataset.get("name"))
    }
    report_paths = {
        normalize_report_path(report)
        for report in reports or []
        if normalize_report_path(report)
    }
    return InternalIndexes(
        theory_paths=theory_paths,
        task_ids=task_ids,
        project_ids=project_ids,
        milestone_ids=milestone_ids,
        practice_ids=practice_ids,
        dataset_names=dataset_names,
        report_paths=report_paths,
    )


def parse_milestone_target(target: InternalTarget) -> tuple[str, str]:
    project_id = normalize_identifier(target.project_id)
    milestone_id = normalize_identifier(target.milestone_id)
    if project_id and milestone_id:
        return project_id, milestone_id

    raw = str(target.target_id or "").strip()
    for separator in ("::", "/", ":"):
        if separator in raw:
            left, right = raw.split(separator, 1)
            return normalize_identifier(left), normalize_identifier(right)
    return project_id, milestone_id


def validate_internal_target(target: InternalTarget, indexes: InternalIndexes) -> InternalTargetResult:
    kind = normalize_identifier(target.kind)
    if kind not in VALID_INTERNAL_TARGET_KINDS:
        return InternalTargetResult(target, False, f"unknown target kind: {target.kind}")

    if kind == "theory_note":
        path = normalize_relative_path(target.path or target.target_id)
        if not path:
            return InternalTargetResult(target, False, "missing theory note path")
        if path in indexes.theory_paths:
            return InternalTargetResult(target, True, resolved=path)
        return InternalTargetResult(target, False, f"theory note not found: {target.path or target.target_id}")

    if kind == "task":
        target_id = normalize_identifier(target.target_id)
        if not target_id:
            return InternalTargetResult(target, False, "missing task id")
        if target_id in indexes.task_ids:
            return InternalTargetResult(target, True, resolved=target_id)
        return InternalTargetResult(target, False, f"task not found: {target.target_id}")

    if kind == "project":
        target_id = normalize_identifier(target.target_id)
        if not target_id:
            return InternalTargetResult(target, False, "missing project id")
        if target_id in indexes.project_ids:
            return InternalTargetResult(target, True, resolved=target_id)
        return InternalTargetResult(target, False, f"project not found: {target.target_id}")

    if kind == "milestone":
        project_id, milestone_id = parse_milestone_target(target)
        if not project_id or not milestone_id:
            return InternalTargetResult(target, False, "missing project id or milestone id")
        if (project_id, milestone_id) in indexes.milestone_ids:
            return InternalTargetResult(target, True, resolved=f"{project_id}::{milestone_id}")
        return InternalTargetResult(target, False, f"milestone not found: {project_id}::{milestone_id}")

    if kind == "practice":
        target_id = normalize_identifier(target.target_id)
        if not target_id:
            return InternalTargetResult(target, False, "missing practice id")
        if target_id in indexes.practice_ids:
            return InternalTargetResult(target, True, resolved=target_id)
        return InternalTargetResult(target, False, f"practice card not found: {target.target_id}")

    if kind == "dataset":
        target_id = normalize_identifier(target.target_id or target.path)
        if not target_id:
            return InternalTargetResult(target, False, "missing dataset name")
        if target_id in indexes.dataset_names:
            return InternalTargetResult(target, True, resolved=target_id)
        return InternalTargetResult(target, False, f"dataset not found: {target.target_id or target.path}")

    report_path = normalize_report_path(target.path or target.target_id)
    if not report_path:
        return InternalTargetResult(target, False, "missing report path")
    if report_path in indexes.report_paths:
        return InternalTargetResult(target, True, resolved=report_path)
    return InternalTargetResult(target, False, f"report not found: {target.path or target.target_id}")
