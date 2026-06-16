from __future__ import annotations

from typing import Any


VALID_MILESTONE_TYPES = {"reading", "code", "visualization", "reflection", "report", "model_card"}

VISUALIZATION_QUALITY_CHECKLIST = [
    "title",
    "axis labels",
    "readable categories",
    "correct chart type",
    "useful insight",
    "no misleading scale",
    "portfolio-ready explanation",
]


def as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalize_milestone(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    milestone_id = str(raw.get("id") or "").strip()
    title = str(raw.get("title") or "").strip()
    milestone_type = str(raw.get("type") or "").strip().casefold()
    description = str(raw.get("description") or "").strip()

    if not milestone_id or not title or not description:
        return None
    if milestone_type not in VALID_MILESTONE_TYPES:
        return None

    return {
        "id": milestone_id,
        "title": title,
        "type": milestone_type,
        "description": description,
        "dataset_hints": as_string_list(raw.get("dataset_hints")),
        "starter_code": str(raw.get("starter_code") or "").strip(),
        "test_code": str(raw.get("test_code") or "").strip(),
        "checklist": as_string_list(raw.get("checklist")),
        "quality_checklist": as_string_list(raw.get("quality_checklist"))
        or (VISUALIZATION_QUALITY_CHECKLIST.copy() if milestone_type == "visualization" else []),
        "reflection_prompt": str(raw.get("reflection_prompt") or "").strip(),
        "portfolio_output": str(raw.get("portfolio_output") or "").strip(),
        "required": bool(raw.get("required", True)),
    }


def normalize_portfolio_templates(value: Any) -> list[dict[str, str]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []

    templates: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        what_to_write = str(item.get("what_to_write") or "").strip()
        chart_or_table = str(item.get("chart_or_table") or "").strip()
        readme_bullet = str(item.get("readme_bullet") or "").strip()
        if not any([title, what_to_write, chart_or_table, readme_bullet]):
            continue
        templates.append(
            {
                "title": title or "Portfolio output",
                "what_to_write": what_to_write,
                "chart_or_table": chart_or_table,
                "readme_bullet": readme_bullet,
            }
        )
    return templates


def normalize_project_recipe(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    project_id = str(raw.get("id") or "").strip()
    title = str(raw.get("title") or "").strip()
    goal = str(raw.get("goal") or "").strip()
    milestones = [
        milestone
        for milestone in (normalize_milestone(item) for item in raw.get("milestones", []))
        if milestone is not None
    ]

    if not project_id or not title or not goal or not milestones:
        return None

    datasets = as_string_list(raw.get("datasets"))
    related_dataset_names = as_string_list(raw.get("related_dataset_names")) or datasets

    return {
        "id": project_id,
        "title": title,
        "level": str(raw.get("level") or "beginner").strip(),
        "track": str(raw.get("track") or "Data Lab").strip(),
        "datasets": datasets,
        "skills": as_string_list(raw.get("skills")),
        "estimated_time": str(raw.get("estimated_time") or "").strip(),
        "goal": goal,
        "business_context": str(raw.get("business_context") or "").strip(),
        "prerequisites": as_string_list(raw.get("prerequisites")),
        "related_theory_paths": as_string_list(raw.get("related_theory_paths")),
        "related_practice_ids": as_string_list(raw.get("related_practice_ids")),
        "related_task_ids": as_string_list(raw.get("related_task_ids")),
        "related_dataset_names": related_dataset_names,
        "related_portfolio_templates": normalize_portfolio_templates(raw.get("related_portfolio_templates")),
        "milestones": milestones,
        "deliverables": as_string_list(raw.get("deliverables")),
        "portfolio_prompt": str(raw.get("portfolio_prompt") or "").strip(),
    }


def required_milestone_ids(project: dict[str, Any]) -> set[str]:
    milestones = project.get("milestones", [])
    if not isinstance(milestones, list):
        return set()
    return {
        str(milestone.get("id"))
        for milestone in milestones
        if isinstance(milestone, dict) and milestone.get("required", True) is True and str(milestone.get("id") or "")
    }


def project_completion(project: dict[str, Any], completed_milestones: set[str]) -> dict[str, Any]:
    required = required_milestone_ids(project)
    done_required = required & completed_milestones
    missing = sorted(required - completed_milestones)
    return {
        "required_total": len(required),
        "required_done": len(done_required),
        "missing_required": missing,
        "complete": not missing,
    }


def checklist_progress(checklist: list[str], checked_items: set[str]) -> dict[str, Any]:
    normalized = [str(item).strip() for item in checklist if str(item).strip()]
    checked = {str(item).strip() for item in checked_items if str(item).strip()}
    done = sum(1 for item in normalized if item in checked)
    total = len(normalized)
    return {
        "total": total,
        "done": done,
        "todo": total - done,
        "ratio": done / total if total else 1.0,
        "complete": done == total,
    }


def project_progress(project: dict[str, Any], completed_milestones: set[str]) -> dict[str, Any]:
    milestones = project.get("milestones", [])
    total = len(milestones) if isinstance(milestones, list) else 0
    done = sum(
        1
        for milestone in milestones
        if isinstance(milestone, dict) and str(milestone.get("id")) in completed_milestones
    )
    ratio = done / total if total else 0.0
    stats = {"total": total, "done": done, "todo": total - done, "ratio": ratio}
    stats.update(project_completion(project, completed_milestones))
    return stats


def calculate_readiness(checks: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [
        {
            "label": str(item.get("label") or "").strip(),
            "done": bool(item.get("done")),
            "kind": str(item.get("kind") or "").strip(),
        }
        for item in checks
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    total = len(normalized)
    done = sum(1 for item in normalized if item["done"])
    missing = [item["label"] for item in normalized if not item["done"]]
    ratio = done / total if total else 1.0
    if not total or done == total:
        status = "ready"
    elif ratio >= 0.6:
        status = "almost ready"
    else:
        status = "not ready"
    return {
        "total": total,
        "done": done,
        "missing": missing,
        "ratio": ratio,
        "status": status,
    }
