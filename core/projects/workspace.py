from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_ROOT_NAME = "user_projects"


def safe_project_slug(value: str, *, fallback: str = "project") -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:80].strip("-") or fallback


def project_workspace_path(project: dict[str, Any], workspace_root: str | Path) -> Path:
    raw_slug = str(project.get("id") or project.get("title") or "project")
    return Path(workspace_root) / safe_project_slug(raw_slug)


def relative_dataset_reference(project_root: str | Path, workspace_path: str | Path, dataset_name: str) -> str:
    dataset_path = Path(project_root) / "datasets" / dataset_name
    return Path(os.path.relpath(dataset_path, start=Path(workspace_path))).as_posix()


def markdown_list(items: list[str], *, fallback: str = "TBD") -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        cleaned = [fallback]
    return "\n".join(f"- {item}" for item in cleaned)


def project_dataset_refs(project: dict[str, Any], project_root: str | Path, workspace_path: str | Path) -> list[str]:
    datasets = project.get("related_dataset_names") or project.get("datasets") or []
    return [relative_dataset_reference(project_root, workspace_path, str(dataset)) for dataset in datasets]


def render_workspace_readme(project: dict[str, Any], dataset_refs: list[str]) -> str:
    milestones = project.get("milestones", [])
    milestone_lines = [
        f"{index}. {milestone.get('title', milestone.get('id', 'Milestone'))} ({milestone.get('type', 'unknown')})"
        for index, milestone in enumerate(milestones, start=1)
        if isinstance(milestone, dict)
    ]
    return "\n".join(
        [
            f"# {project.get('title', 'Project Workspace')}",
            "",
            "## Goal",
            str(project.get("goal") or "TBD"),
            "",
            "## Business Context",
            str(project.get("business_context") or "TBD"),
            "",
            "## Datasets",
            markdown_list(dataset_refs, fallback="No dataset required."),
            "",
            "Do not copy raw datasets into this workspace. Read them from the app-level `datasets/` folder.",
            "",
            "## Skills",
            markdown_list([str(item) for item in project.get("skills", [])]),
            "",
            "## Milestones",
            markdown_list(milestone_lines, fallback="No milestones listed."),
            "",
            "## Deliverables",
            markdown_list([str(item) for item in project.get("deliverables", [])]),
            "",
            "## How To Reproduce Locally",
            "1. Open Hub_ML and run the project milestones in the Notebook or Project runner.",
            "2. Use the dataset paths listed above, for example:",
            '   `pd.read_csv("../../datasets/df_orders.csv")`',
            "3. Save charts into `artifacts/charts/` and derived summary tables into `artifacts/tables/`.",
            "4. Write findings in `portfolio.md` and notes in `notes.md`.",
            "",
            "## Artifact Locations",
            "- Charts: `artifacts/charts/`",
            "- Tables: `artifacts/tables/`",
            "- Optional reusable code: `src/`",
            "- Portfolio writeup: `portfolio.md`",
            "",
        ]
    )


def render_portfolio_markdown_template(project: dict[str, Any]) -> str:
    resume_bullets: list[str] = []
    for template in project.get("related_portfolio_templates", []):
        if isinstance(template, dict) and str(template.get("readme_bullet") or "").strip():
            resume_bullets.append(str(template["readme_bullet"]).strip())

    return "\n".join(
        [
            f"# {project.get('title', 'Project')} Portfolio Draft",
            "",
            "> Fill this with real findings from your run. Do not invent metrics or include raw/private data.",
            "",
            "## Problem",
            "TBD",
            "",
            "## Data",
            "TBD",
            "",
            "## Approach",
            "TBD",
            "",
            "## Key Results",
            "TBD",
            "",
            "## Visualizations",
            "TBD",
            "",
            "## Limitations",
            "TBD",
            "",
            "## Next Steps",
            "TBD",
            "",
            "## Resume Bullet Draft",
            markdown_list(resume_bullets, fallback="TBD"),
            "",
        ]
    )


def render_notes_template(project: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Notes: {project.get('title', 'Project')}",
            "",
            "## Decisions",
            "- TBD",
            "",
            "## Questions",
            "- TBD",
            "",
            "## Observations",
            "- TBD",
            "",
        ]
    )


def render_milestones_markdown(project: dict[str, Any]) -> str:
    sections: list[str] = [f"# Milestones: {project.get('title', 'Project')}", ""]
    for milestone in project.get("milestones", []):
        if not isinstance(milestone, dict):
            continue
        sections.extend(
            [
                f"## {milestone.get('title', milestone.get('id', 'Milestone'))}",
                "",
                f"- ID: `{milestone.get('id', '')}`",
                f"- Type: `{milestone.get('type', '')}`",
                f"- Required: `{bool(milestone.get('required', True))}`",
                "",
                str(milestone.get("description") or "TBD"),
                "",
                "### Checklist",
                markdown_list([str(item) for item in milestone.get("checklist", [])], fallback="TBD"),
                "",
                "### Portfolio Output",
                str(milestone.get("portfolio_output") or "TBD"),
                "",
            ]
        )
    return "\n".join(sections)


def workspace_manifest(project: dict[str, Any], created_at: str) -> dict[str, Any]:
    return {
        "project_id": project.get("id", ""),
        "project_title": project.get("title", ""),
        "created_at": created_at,
        "source_recipe_path": project.get("source_path", ""),
        "datasets": project.get("related_dataset_names") or project.get("datasets") or [],
        "milestone_ids": [
            milestone.get("id", "")
            for milestone in project.get("milestones", [])
            if isinstance(milestone, dict)
        ],
        "status": "created",
    }


def project_workspace_files(
    project: dict[str, Any],
    workspace_path: str | Path,
    project_root: str | Path,
    created_at: str,
) -> dict[str, str]:
    dataset_refs = project_dataset_refs(project, project_root, workspace_path)
    manifest = workspace_manifest(project, created_at)
    return {
        "README.md": render_workspace_readme(project, dataset_refs),
        "project.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        "portfolio.md": render_portfolio_markdown_template(project),
        "notes.md": render_notes_template(project),
        "milestones.md": render_milestones_markdown(project),
        "artifacts/charts/.gitkeep": "",
        "artifacts/tables/.gitkeep": "",
        "src/.gitkeep": "",
    }


def create_project_workspace(
    project: dict[str, Any],
    workspace_root: str | Path,
    project_root: str | Path,
    *,
    overwrite: bool = False,
    created_at: str | None = None,
) -> dict[str, Any]:
    workspace_path = project_workspace_path(project, workspace_root)
    if workspace_path.exists() and not overwrite:
        return {
            "created": False,
            "exists": True,
            "path": str(workspace_path),
            "written": [],
        }

    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    files = project_workspace_files(project, workspace_path, project_root, timestamp)
    workspace_path.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for relative_path, content in files.items():
        target = workspace_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(relative_path)

    return {
        "created": True,
        "exists": False,
        "path": str(workspace_path),
        "written": written,
    }
