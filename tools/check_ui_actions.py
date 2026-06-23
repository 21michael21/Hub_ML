from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.datasets.registry import scan_datasets
from core.internal_links import build_internal_indexes
from core.projects.loader import load_project_recipes_from_dirs
from core.tasks.loader import load_mentor_tasks
from core.ui_actions import UIAction, UIActionIndexes, UIActionResult, validate_ui_actions
from tools.check_internal_links import load_practice_cards, scan_notes


DEFAULT_VAULT = Path("/Users/mihailkulibaba/Projects/practic_ML/obsidian_vkat")
PROJECT_DIRS = (
    ROOT / "content" / "projects" / "data_lab",
    ROOT / "content" / "projects" / "ml_lab",
)
REPORT_FILES = (
    ROOT / "content" / "reports" / "content_gate_report.json",
    ROOT / "content" / "reports" / "coverage_report.json",
    ROOT / "content" / "reports" / "theory_audit.json",
    ROOT / "content" / "reports" / "internal_links_report.json",
)
TAB_TARGETS = {
    "Home",
    "Theory",
    "Practice",
    "Theory Quality",
    "Roadmap",
    "Progress",
    "Data Lab",
    "ML Lab",
    "Notebook",
    "Datasets",
    "Tasks",
    "Algorithms",
    "Interviews",
    "Portfolio",
    "Experiments",
    "Architecture",
    "Links Health",
    "Home",
    "🎯 Practice",
    "🎯 Tasks",
    "🧪 Data Lab Projects",
    "🤖 ML Lab",
    "📓 Notebook",
    "📊 Datasets",
    "🧩 Algorithms",
    "🎤 Interviews",
    "📁 Portfolio",
    "🧪 Experiments",
    "🏗 Architecture",
    "🧭 Theory Quality",
}
NAVIGATION_TARGETS = {
    "Home",
    "Theory",
    "🎯 Practice",
    "🎯 Tasks",
    "🧪 Data Lab Projects",
    "🤖 ML Lab",
    "📓 Notebook",
    "📊 Datasets",
    "🧩 Algorithms",
    "🎤 Interviews",
    "📁 Portfolio",
    "🧪 Experiments",
    "🏗 Architecture",
    "🧭 Theory Quality",
    "Roadmap",
    "Progress",
    "Links Health",
}
KNOWN_STATE_KEYS = {
    "active_tab",
    "active_note_path",
    "note_radio",
    "selected_practice_card",
    "selected_mentor_task",
    "selected_data_lab_project",
    "tasks_plain_editor",
    "project_milestones_plain_editor",
    "interview_practice_mode",
    "interview_company_filter",
    "portfolio_export_projects",
    "portfolio_export_cards",
    "learning_progress",
    "data_lab_projects",
}


def slug(value: object) -> str:
    return "".join(char if char.isalnum() else "_" for char in str(value or "").strip().casefold()).strip("_") or "item"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def first(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return items[0] if items else None


def build_navigation_actions() -> list[UIAction]:
    return [
        UIAction(
            action_id=f"nav.{slug(tab)}",
            label=f"Open {tab}",
            action_type="navigate",
            target_kind="tab",
            target_id=tab,
            required_state_keys=("active_tab",),
            expected_state_changes=("active_tab",),
            source="sidebar",
        )
        for tab in sorted(NAVIGATION_TARGETS)
    ]


def build_home_actions(
    notes: list[dict[str, Any]],
    practice_cards: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    projects: list[dict[str, Any]],
) -> list[UIAction]:
    actions: list[UIAction] = []
    note = first(notes)
    if note:
        actions.append(
            UIAction(
                action_id="home.today.open_theory",
                label="Открыть теорию",
                action_type="navigate",
                target_kind="theory_note",
                path=str(note.get("relative_path") or ""),
                required_state_keys=("active_tab", "active_note_path"),
                expected_state_changes=("active_tab", "active_note_path"),
                source="home.today",
            )
        )
    card = first(practice_cards)
    if card:
        actions.append(
            UIAction(
                action_id="home.today.open_practice",
                label="Открыть практику",
                action_type="navigate",
                target_kind="practice",
                target_id=str(card.get("id") or ""),
                required_state_keys=("active_tab", "selected_practice_card"),
                expected_state_changes=("active_tab", "selected_practice_card"),
                source="home.today",
            )
        )
    task = first(tasks)
    if task:
        actions.append(
            UIAction(
                action_id="home.today.open_task",
                label="Открыть задачу",
                action_type="navigate",
                target_kind="task",
                target_id=str(task.get("id") or ""),
                required_state_keys=("active_tab", "selected_mentor_task"),
                expected_state_changes=("active_tab", "selected_mentor_task"),
                source="home.today",
            )
        )
    project = first(projects)
    if project:
        project_id = str(project.get("id") or "")
        actions.append(
            UIAction(
                action_id="home.today.open_project",
                label="Открыть проект",
                action_type="navigate",
                target_kind="project",
                target_id=project_id,
                required_state_keys=("active_tab", "selected_data_lab_project"),
                expected_state_changes=("active_tab", "selected_data_lab_project"),
                source="home.today",
            )
        )
        milestone = first([item for item in project.get("milestones", []) if isinstance(item, dict)])
        if milestone:
            actions.append(
                UIAction(
                    action_id="home.today.open_project_milestone",
                    label="Открыть milestone проекта",
                    action_type="navigate",
                    target_kind="milestone",
                    project_id=project_id,
                    milestone_id=str(milestone.get("id") or ""),
                    required_state_keys=("active_tab", "selected_data_lab_project"),
                    expected_state_changes=("active_tab", "selected_data_lab_project"),
                    source="home.resume",
                )
            )
    return actions


def build_theory_quality_actions(audit_report: dict[str, Any]) -> list[UIAction]:
    summary = audit_report.get("summary") if isinstance(audit_report.get("summary"), dict) else {}
    notes = summary.get("weakest_notes") if isinstance(summary.get("weakest_notes"), list) else []
    actions: list[UIAction] = []
    for index, note in enumerate(notes[:20]):
        if not isinstance(note, dict):
            continue
        relative_path = str(note.get("relative_path") or "")
        if not relative_path:
            continue
        actions.append(
            UIAction(
                action_id=f"theory_quality.open_weak_note.{index}.{slug(relative_path)}",
                label=f"Открыть в Theory: {relative_path}",
                action_type="navigate",
                target_kind="theory_note",
                path=relative_path,
                required_state_keys=("active_tab", "active_note_path"),
                expected_state_changes=("active_tab", "active_note_path"),
                source="theory_quality.weakest_notes",
            )
        )
    return actions


def build_practice_actions(practice_cards: list[dict[str, Any]]) -> list[UIAction]:
    actions: list[UIAction] = []
    for card in practice_cards:
        card_id = str(card.get("id") or "")
        if not card_id:
            continue
        actions.append(
            UIAction(
                action_id=f"practice.open.{slug(card_id)}",
                label=f"Open practice: {card.get('title') or card_id}",
                action_type="open_detail",
                target_kind="practice",
                target_id=card_id,
                required_state_keys=("selected_practice_card",),
                expected_state_changes=("selected_practice_card",),
                source="practice.card",
            )
        )
        related_note = str(card.get("related_note") or "").strip()
        if related_note:
            actions.append(
                UIAction(
                    action_id=f"practice.open_related_note.{slug(card_id)}",
                    label=f"Open related note: {related_note}",
                    action_type="navigate",
                    target_kind="theory_note",
                    path=related_note,
                    required_state_keys=("active_tab", "active_note_path"),
                    expected_state_changes=("active_tab", "active_note_path"),
                    source="practice.related_note",
                )
            )
        dataset = str(card.get("dataset") or "").strip()
        if dataset:
            actions.append(
                UIAction(
                    action_id=f"practice.open_dataset.{slug(card_id)}",
                    label=f"Open dataset: {dataset}",
                    action_type="navigate",
                    target_kind="dataset",
                    target_id=dataset,
                    required_state_keys=("active_tab",),
                    expected_state_changes=("active_tab",),
                    source="practice.dataset",
                )
            )
    return actions


def build_task_actions(tasks: list[dict[str, Any]]) -> list[UIAction]:
    actions: list[UIAction] = []
    for task in tasks:
        task_id = str(task.get("id") or "")
        if not task_id:
            continue
        actions.append(
            UIAction(
                action_id=f"tasks.open.{slug(task_id)}",
                label=f"Open task: {task.get('title') or task_id}",
                action_type="open_detail",
                target_kind="task",
                target_id=task_id,
                required_state_keys=("selected_mentor_task",),
                expected_state_changes=("selected_mentor_task",),
                source="tasks.list",
            )
        )
        actions.append(
            UIAction(
                action_id=f"tasks.run_check.{slug(task_id)}",
                label=f"Run task checks: {task.get('title') or task_id}",
                action_type="run_check",
                target_kind="task",
                target_id=task_id,
                required_state_keys=("selected_mentor_task",),
                safe_to_e2e_click=False,
                source="tasks.detail",
            )
        )
    return actions


def build_project_actions(projects: list[dict[str, Any]]) -> list[UIAction]:
    actions: list[UIAction] = []
    for project in projects:
        project_id = str(project.get("id") or "")
        if not project_id:
            continue
        actions.append(
            UIAction(
                action_id=f"projects.open.{slug(project_id)}",
                label=f"Open project: {project.get('title') or project_id}",
                action_type="open_detail",
                target_kind="project",
                target_id=project_id,
                required_state_keys=("selected_data_lab_project",),
                expected_state_changes=("selected_data_lab_project",),
                source="projects.catalog",
            )
        )
        if str(project.get("track") or "").casefold() == "classic ml":
            actions.append(
                UIAction(
                    action_id=f"experiments.save.{slug(project_id)}",
                    label=f"Save experiment record: {project.get('title') or project_id}",
                    action_type="save_progress",
                    target_kind="project",
                    target_id=project_id,
                    required_state_keys=("selected_data_lab_project",),
                    safe_to_e2e_click=False,
                    source="ml_lab.experiment_tracker",
                )
            )
        for milestone in project.get("milestones", []):
            if not isinstance(milestone, dict):
                continue
            milestone_id = str(milestone.get("id") or "")
            if not milestone_id:
                continue
            target = {
                "target_kind": "milestone",
                "project_id": project_id,
                "milestone_id": milestone_id,
            }
            actions.append(
                UIAction(
                    action_id=f"projects.milestone.mark_done.{slug(project_id)}.{slug(milestone_id)}",
                    label=f"Mark milestone done: {milestone.get('title') or milestone_id}",
                    action_type="save_progress",
                    required_state_keys=("learning_progress",),
                    safe_to_e2e_click=False,
                    source="projects.milestone",
                    **target,
                )
            )
            actions.append(
                UIAction(
                    action_id=f"projects.milestone.run.{slug(project_id)}.{slug(milestone_id)}",
                    label=f"Run milestone: {milestone.get('title') or milestone_id}",
                    action_type="run_check",
                    required_state_keys=("learning_progress",),
                    safe_to_e2e_click=False,
                    source="projects.milestone",
                    **target,
                )
            )
    return actions


def build_portfolio_actions() -> list[UIAction]:
    return [
        UIAction(
            action_id="portfolio.preview",
            label="Markdown preview",
            action_type="set_state",
            required_state_keys=("portfolio_export_projects", "portfolio_export_cards"),
            source="portfolio.exporter",
        ),
        UIAction(
            action_id="portfolio.export_markdown",
            label="Export markdown",
            action_type="export",
            required_state_keys=("portfolio_export_projects", "portfolio_export_cards"),
            safe_to_e2e_click=False,
            source="portfolio.exporter",
        ),
    ]


def build_interview_actions() -> list[UIAction]:
    actions = [
        UIAction(
            action_id=f"interviews.mode.{slug(mode)}",
            label=f"Switch interview mode: {mode}",
            action_type="set_state",
            target_kind="tab",
            target_id="Interviews",
            required_state_keys=("interview_practice_mode",),
            expected_state_changes=("interview_practice_mode",),
            source="interviews.mode",
        )
        for mode in ("Learn", "Practice", "Timed Mock", "Review")
    ]
    actions.append(
        UIAction(
            action_id="interviews.save_answer",
            label="Save answer",
            action_type="save_progress",
            target_kind="tab",
            target_id="Interviews",
            required_state_keys=("interview_practice_mode",),
            safe_to_e2e_click=False,
            source="interviews.answer",
        )
    )
    return actions


def build_actions(loaded: dict[str, Any]) -> list[UIAction]:
    return [
        *build_navigation_actions(),
        *build_home_actions(
            loaded["notes"],
            loaded["practice_cards"],
            loaded["tasks"],
            loaded["projects"],
        ),
        *build_theory_quality_actions(loaded["audit_report"]),
        *build_practice_actions(loaded["practice_cards"]),
        *build_task_actions(loaded["tasks"]),
        *build_project_actions(loaded["projects"]),
        *build_portfolio_actions(),
        *build_interview_actions(),
    ]


def load_action_context(vault: Path | None) -> dict[str, Any]:
    notes = scan_notes(vault)
    tasks = load_mentor_tasks(ROOT / "content" / "extracted" / "mentor_tasks.json").get("tasks", [])
    projects = load_project_recipes_from_dirs(PROJECT_DIRS)
    practice_cards = load_practice_cards(ROOT / "practice")
    datasets = scan_datasets(ROOT / "datasets")
    reports = [path for path in REPORT_FILES if path.exists()]
    indexes = build_internal_indexes(
        notes=notes,
        tasks=tasks,
        projects=projects,
        practice_cards=practice_cards,
        datasets=datasets,
        reports=reports,
    )
    return {
        "notes": notes,
        "tasks": tasks,
        "projects": projects,
        "practice_cards": practice_cards,
        "datasets": datasets,
        "reports": reports,
        "audit_report": load_json(ROOT / "content" / "reports" / "theory_audit.json"),
        "indexes": UIActionIndexes(indexes, set(KNOWN_STATE_KEYS), set(TAB_TARGETS)),
        "metadata": {
            "vault": str(vault) if vault else "",
            "notes": len(notes),
            "tasks": len(tasks),
            "projects": len(projects),
            "practice_cards": len(practice_cards),
            "datasets": len(datasets),
            "reports": len(reports),
            "known_state_keys": sorted(KNOWN_STATE_KEYS),
        },
    }


def result_to_dict(result: UIActionResult) -> dict[str, Any]:
    return {
        "action": asdict(result.action),
        "ok": result.ok,
        "severity": result.severity,
        "reason": result.reason,
        "target_exists": result.target_exists,
        "state_keys_ok": result.state_keys_ok,
        "duplicate": result.duplicate,
    }


def action_inventory(actions: list[UIAction]) -> dict[str, dict[str, int]]:
    inventory: dict[str, dict[str, int]] = {
        "by_action_type": {},
        "by_target_kind": {},
        "by_source": {},
    }
    for action in actions:
        action_type = action.action_type or "unknown"
        target_kind = action.target_kind or "none"
        source = action.source or "unknown"
        inventory["by_action_type"][action_type] = inventory["by_action_type"].get(action_type, 0) + 1
        inventory["by_target_kind"][target_kind] = inventory["by_target_kind"].get(target_kind, 0) + 1
        inventory["by_source"][source] = inventory["by_source"].get(source, 0) + 1
    return {
        group: dict(sorted(values.items()))
        for group, values in inventory.items()
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# UI Actions Health Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Total actions: {summary['total']}",
        f"- Passing: {summary['passing']}",
        f"- Warnings / unsafe: {summary['warnings']}",
        f"- Broken: {summary['broken']}",
        "",
        "## Broken Actions",
        "",
    ]
    broken = report["broken_actions"]
    if not broken:
        lines.append("All UI actions have valid targets and state keys.")
    else:
        for item in broken:
            action = item["action"]
            lines.extend(
                [
                    f"### {action['action_id']} — {action['label']}",
                    f"- Type: `{action['action_type']}`",
                    f"- Source: `{action.get('source', '')}`",
                    f"- Target: `{action.get('target_kind', '')}:{action.get('target_id') or action.get('path') or action.get('milestone_id')}`",
                    f"- Reason: {item['reason']}",
                    "",
                ]
            )
    warnings = report["unsafe_actions"]
    lines.extend(["", "## Unsafe For Automated Clicking", ""])
    if not warnings:
        lines.append("No unsafe actions reported.")
    else:
        for item in warnings:
            action = item["action"]
            lines.append(f"- `{action['action_id']}` — {action['label']} ({item['reason']})")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Hub_ML UI action targets and state keys.")
    parser.add_argument("--vault", default=os.environ.get("VAULT_PATH", str(DEFAULT_VAULT)))
    parser.add_argument("--output-dir", default=str(ROOT / "content" / "reports"))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when broken actions exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = Path(args.vault).expanduser() if args.vault else None
    if vault is not None and not vault.exists():
        print(f"warning: vault not found, theory-note actions will be limited: {vault}", file=sys.stderr)
        vault = None

    loaded = load_action_context(vault)
    actions = build_actions(loaded)
    results = validate_ui_actions(actions, loaded["indexes"])
    broken = [result for result in results if not result.ok]
    warnings = [result for result in results if result.severity == "warning"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": loaded["metadata"],
        "summary": {
            "total": len(results),
            "passing": len(results) - len(broken),
            "warnings": len(warnings),
            "broken": len(broken),
        },
        "inventory": action_inventory(actions),
        "broken_actions": [result_to_dict(result) for result in broken],
        "unsafe_actions": [result_to_dict(result) for result in warnings],
    }

    output_dir = Path(args.output_dir)
    output_json = output_dir / "ui_actions_report.json"
    output_md = output_dir / "ui_actions_report.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown_report(report), encoding="utf-8")
    print(
        f"UI ACTIONS: {report['summary']['passing']}/{report['summary']['total']} pass, "
        f"{report['summary']['warnings']} unsafe, {report['summary']['broken']} broken"
    )
    print(f"Wrote: {output_json}")
    print(f"Wrote: {output_md}")
    return 1 if args.strict and broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
