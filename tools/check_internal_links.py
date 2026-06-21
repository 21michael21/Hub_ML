from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.datasets.registry import scan_datasets
from core.internal_links import (
    InternalTarget,
    build_internal_indexes,
    validate_internal_target,
)
from core.projects.loader import load_project_recipes_from_dirs
from core.tasks.loader import load_mentor_tasks


DEFAULT_VAULT = Path("/Users/mihailkulibaba/Projects/practic_ML/obsidian_vkat")
PROJECT_DIRS = (
    ROOT / "content" / "projects" / "data_lab",
    ROOT / "content" / "projects" / "ml_lab",
)
REPORT_FILES = (
    ROOT / "content" / "reports" / "content_gate_report.json",
    ROOT / "content" / "reports" / "content_gate_report.md",
    ROOT / "content" / "reports" / "coverage_report.json",
    ROOT / "content" / "reports" / "coverage_report.md",
    ROOT / "content" / "reports" / "theory_audit.json",
    ROOT / "content" / "reports" / "theory_audit.md",
)
OUTPUT_JSON = ROOT / "content" / "reports" / "internal_links_report.json"
OUTPUT_MD = ROOT / "content" / "reports" / "internal_links_report.md"
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


def is_hidden_path(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part.startswith(".") for part in relative.parts)


def scan_notes(vault: Path | None) -> list[dict[str, Any]]:
    if vault is None or not vault.exists() or not vault.is_dir():
        return []
    notes: list[dict[str, Any]] = []
    for note_path in sorted(vault.rglob("*.md"), key=lambda item: item.as_posix().casefold()):
        if is_hidden_path(note_path, vault):
            continue
        relative_path = note_path.relative_to(vault).as_posix()
        section = relative_path.split("/", 1)[0] if "/" in relative_path else "Без раздела"
        notes.append(
            {
                "relative_path": relative_path,
                "section": section,
                "title": note_path.stem.replace("_", " "),
            }
        )
    return notes


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    block = match.group(1)
    body = text[match.end() :]
    fields: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) and current_key:
            item = line.strip()
            if item.startswith("- "):
                fields.setdefault(current_key, [])
                if isinstance(fields[current_key], list):
                    fields[current_key].append(item[2:].strip().strip("\"'"))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        if not value:
            fields[current_key] = []
        elif value.startswith("[") and value.endswith("]"):
            fields[current_key] = [item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
        else:
            fields[current_key] = value.strip().strip("\"'")
    return fields, body


def load_practice_cards(practice_dir: Path) -> list[dict[str, Any]]:
    if not practice_dir.exists():
        return []
    cards: list[dict[str, Any]] = []
    for card_path in sorted(practice_dir.glob("*.md"), key=lambda item: item.name.casefold()):
        text = card_path.read_text(encoding="utf-8", errors="replace")
        fields, body = parse_frontmatter(text)
        cards.append(
            {
                "id": card_path.stem,
                "path": card_path.as_posix(),
                "title": fields.get("title") or card_path.stem,
                "related_note": fields.get("related_note") or "",
                "dataset": fields.get("dataset") or "",
                "text": body,
            }
        )
    return cards


def first_or_none(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return items[0] if items else None


def build_home_targets(
    *,
    notes: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    projects: list[dict[str, Any]],
    practice_cards: list[dict[str, Any]],
    datasets: list[dict[str, Any]],
) -> list[InternalTarget]:
    targets: list[InternalTarget] = []
    note = first_or_none(notes)
    if note:
        targets.append(
            InternalTarget(
                kind="theory_note",
                label=f"Home next theory note: {note['relative_path']}",
                path=str(note["relative_path"]),
                source="home",
            )
        )
    task = first_or_none(tasks)
    if task:
        targets.append(
            InternalTarget(
                kind="task",
                label=f"Home next mentor task: {task.get('title', task.get('id', 'task'))}",
                target_id=str(task.get("id") or ""),
                source="home",
            )
        )
    project = first_or_none(projects)
    if project:
        targets.append(
            InternalTarget(
                kind="project",
                label=f"Home next project: {project.get('title', project.get('id', 'project'))}",
                target_id=str(project.get("id") or ""),
                source="home",
            )
        )
        milestone = first_or_none(list(project.get("milestones", [])))
        if milestone:
            targets.append(
                InternalTarget(
                    kind="milestone",
                    label=f"Home next project milestone: {milestone.get('title', milestone.get('id', 'milestone'))}",
                    project_id=str(project.get("id") or ""),
                    milestone_id=str(milestone.get("id") or ""),
                    source="home",
                )
            )
    card = first_or_none(practice_cards)
    if card:
        targets.append(
            InternalTarget(
                kind="practice",
                label=f"Home next practice card: {card.get('title', card.get('id', 'practice'))}",
                target_id=str(card.get("id") or ""),
                source="home",
            )
        )
    dataset = first_or_none(datasets)
    if dataset:
        targets.append(
            InternalTarget(
                kind="dataset",
                label=f"Home dataset shortcut: {dataset.get('name', 'dataset')}",
                target_id=str(dataset.get("name") or ""),
                source="home",
            )
        )
    return targets


def build_project_connection_targets(projects: list[dict[str, Any]]) -> list[InternalTarget]:
    targets: list[InternalTarget] = []
    for project in projects:
        project_id = str(project.get("id") or "")
        project_label = str(project.get("title") or project_id)
        for path in project.get("related_theory_paths", []):
            targets.append(
                InternalTarget(
                    kind="theory_note",
                    label=f"{project_label} theory: {path}",
                    path=str(path),
                    source=f"project:{project_id}",
                )
            )
        for card_id in project.get("related_practice_ids", []):
            targets.append(
                InternalTarget(
                    kind="practice",
                    label=f"{project_label} practice: {card_id}",
                    target_id=str(card_id),
                    source=f"project:{project_id}",
                )
            )
        for task_id in project.get("related_task_ids", []):
            targets.append(
                InternalTarget(
                    kind="task",
                    label=f"{project_label} task: {task_id}",
                    target_id=str(task_id),
                    source=f"project:{project_id}",
                )
            )
        for dataset_name in project.get("related_dataset_names") or project.get("datasets", []):
            targets.append(
                InternalTarget(
                    kind="dataset",
                    label=f"{project_label} dataset: {dataset_name}",
                    target_id=str(dataset_name),
                    source=f"project:{project_id}",
                )
            )
        for milestone in project.get("milestones", []):
            if not isinstance(milestone, dict):
                continue
            targets.append(
                InternalTarget(
                    kind="milestone",
                    label=f"{project_label} milestone: {milestone.get('title', milestone.get('id', 'milestone'))}",
                    project_id=project_id,
                    milestone_id=str(milestone.get("id") or ""),
                    source=f"project:{project_id}",
                )
            )
    return targets


def build_practice_connection_targets(cards: list[dict[str, Any]]) -> list[InternalTarget]:
    targets: list[InternalTarget] = []
    for card in cards:
        card_id = str(card.get("id") or "")
        title = str(card.get("title") or card_id)
        related_note = str(card.get("related_note") or "").strip()
        if related_note:
            targets.append(
                InternalTarget(
                    kind="theory_note",
                    label=f"{title} related note: {related_note}",
                    path=related_note,
                    source=f"practice:{card_id}",
                )
            )
        dataset = str(card.get("dataset") or "").strip()
        if dataset:
            targets.append(
                InternalTarget(
                    kind="dataset",
                    label=f"{title} dataset: {dataset}",
                    target_id=dataset,
                    source=f"practice:{card_id}",
                )
            )
    return targets


def build_report_targets() -> list[InternalTarget]:
    return [
        InternalTarget(
            kind="report",
            label=f"Report file: {path.relative_to(ROOT).as_posix()}",
            path=path.as_posix(),
            source="reports",
        )
        for path in REPORT_FILES
    ]


def load_all_targets(vault: Path | None) -> tuple[list[InternalTarget], dict[str, Any]]:
    notes = scan_notes(vault)
    tasks_data = load_mentor_tasks(ROOT / "content" / "extracted" / "mentor_tasks.json")
    tasks = tasks_data.get("tasks", [])
    projects = load_project_recipes_from_dirs(PROJECT_DIRS)
    practice_cards = load_practice_cards(ROOT / "practice")
    datasets = scan_datasets(ROOT / "datasets")
    reports = [path for path in REPORT_FILES if path.exists()]

    targets: list[InternalTarget] = []
    targets.extend(build_home_targets(notes=notes, tasks=tasks, projects=projects, practice_cards=practice_cards, datasets=datasets))
    targets.extend(build_project_connection_targets(projects))
    targets.extend(build_practice_connection_targets(practice_cards))
    targets.extend(build_report_targets())
    indexes = build_internal_indexes(
        notes=notes,
        tasks=tasks,
        projects=projects,
        practice_cards=practice_cards,
        datasets=datasets,
        reports=reports,
    )
    metadata = {
        "vault": str(vault) if vault else "",
        "notes": len(notes),
        "tasks": len(tasks),
        "projects": len(projects),
        "practice_cards": len(practice_cards),
        "datasets": len(datasets),
        "reports": len(reports),
    }
    return targets, {"indexes": indexes, "metadata": metadata}


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Internal UI Link Health Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Vault: `{report['metadata'].get('vault', '')}`",
        "",
        "## Summary",
        "",
        f"- Total targets: {summary['total']}",
        f"- Passing: {summary['passing']}",
        f"- Broken: {summary['broken']}",
        "",
        "## Broken Targets",
        "",
    ]
    broken = [item for item in report["targets"] if not item["exists"]]
    if not broken:
        lines.append("All internal targets resolved.")
    else:
        for item in broken:
            target = item["target"]
            lines.extend(
                [
                    f"### {target['kind']} — {target['label']}",
                    f"- Source: `{target.get('source', '')}`",
                    f"- Target: `{target.get('target_id') or target.get('path')}`",
                    f"- Reason: {item['reason']}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Hub_ML internal UI/navigation targets.")
    parser.add_argument("--vault", default=os.environ.get("VAULT_PATH", str(DEFAULT_VAULT)))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when broken targets exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = Path(args.vault).expanduser() if args.vault else None
    if vault is not None and not vault.exists():
        print(f"warning: vault not found, theory note targets will be limited: {vault}", file=sys.stderr)
        vault = None

    targets, loaded = load_all_targets(vault)
    indexes = loaded["indexes"]
    results = [validate_internal_target(target, indexes) for target in targets]
    broken = [result for result in results if not result.exists]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": loaded["metadata"],
        "summary": {
            "total": len(results),
            "passing": len(results) - len(broken),
            "broken": len(broken),
        },
        "targets": [
            {
                "target": asdict(result.target),
                "exists": result.exists,
                "reason": result.reason,
                "resolved": result.resolved,
            }
            for result in results
        ],
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown_report(report), encoding="utf-8")
    print(f"INTERNAL LINKS: {report['summary']['passing']}/{report['summary']['total']} pass, {report['summary']['broken']} broken")
    print(f"Wrote: {OUTPUT_JSON}")
    print(f"Wrote: {OUTPUT_MD}")
    return 1 if args.strict and broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
