from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.projects.models import project_completion, project_progress


def completed_milestone_ids(record: dict[str, Any] | None) -> set[str]:
    if not isinstance(record, dict):
        return set()
    milestones = record.get("milestones")
    if not isinstance(milestones, dict):
        return set()
    return {
        str(milestone_id)
        for milestone_id, value in milestones.items()
        if isinstance(value, dict) and value.get("done") is True
    }


def set_milestone_completion(
    record: dict[str, Any] | None,
    milestone_id: str,
    done: bool,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    next_record = dict(record or {})
    milestones = next_record.get("milestones")
    if not isinstance(milestones, dict):
        milestones = {}
    next_record["milestones"] = milestones
    milestone_key = str(milestone_id)
    milestone_record = milestones.get(milestone_key)
    if not isinstance(milestone_record, dict):
        milestone_record = {}
    milestone_record.update(
        {
            "done": bool(done),
            "updated_at": timestamp or datetime.now(timezone.utc).isoformat(),
        }
    )
    milestones[milestone_key] = milestone_record
    next_record["updated_at"] = milestone_record["updated_at"]
    return next_record


def milestone_record(record: dict[str, Any] | None, milestone_id: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    milestones = record.get("milestones")
    if not isinstance(milestones, dict):
        return {}
    value = milestones.get(str(milestone_id), {})
    return value if isinstance(value, dict) else {}


def set_milestone_data(
    record: dict[str, Any] | None,
    milestone_id: str,
    updates: dict[str, Any],
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    next_record = dict(record or {})
    milestones = next_record.get("milestones")
    if not isinstance(milestones, dict):
        milestones = {}
    next_record["milestones"] = milestones
    milestone_key = str(milestone_id)
    current = milestones.get(milestone_key)
    if not isinstance(current, dict):
        current = {}
    current.update(updates)
    current["updated_at"] = timestamp or datetime.now(timezone.utc).isoformat()
    milestones[milestone_key] = current
    next_record["updated_at"] = current["updated_at"]
    return next_record


def set_checklist_item(
    record: dict[str, Any] | None,
    milestone_id: str,
    item: str,
    checked: bool,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    current = milestone_record(record, milestone_id)
    checked_items = current.get("checked_items")
    if not isinstance(checked_items, list):
        checked_items = []
    normalized = [str(value) for value in checked_items]
    item_value = str(item)
    if checked and item_value not in normalized:
        normalized.append(item_value)
    if not checked:
        normalized = [value for value in normalized if value != item_value]
    return set_milestone_data(
        record,
        milestone_id,
        {"checked_items": normalized},
        timestamp=timestamp,
    )


def is_project_complete(record: dict[str, Any] | None) -> bool:
    return isinstance(record, dict) and record.get("complete") is True


def set_project_completion(
    record: dict[str, Any] | None,
    complete: bool,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    next_record = dict(record or {})
    now = timestamp or datetime.now(timezone.utc).isoformat()
    next_record["complete"] = bool(complete)
    next_record["completed_at"] = now if complete else ""
    next_record["updated_at"] = now
    return next_record


def set_project_completion_if_ready(
    project: dict[str, Any],
    record: dict[str, Any] | None,
    complete: bool,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    if complete and not project_completion(project, completed_milestone_ids(record))["complete"]:
        return set_project_completion(record, False, timestamp=timestamp)
    return set_project_completion(record, complete, timestamp=timestamp)


def project_progress_from_record(project: dict[str, Any], record: dict[str, Any] | None) -> dict[str, Any]:
    return project_progress(project, completed_milestone_ids(record))
