from __future__ import annotations

import re
from pathlib import Path
from typing import Any


EXPORT_WARNING = (
    "Generated portfolio text is a template. Fill real findings manually, "
    "do not include private data, and do not commit raw datasets."
)


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def markdown_list(items: list[str], *, fallback: str = "Fill manually.") -> str:
    cleaned = [item.strip() for item in items if item.strip()]
    if not cleaned:
        cleaned = [fallback]
    return "\n".join(f"- {item}" for item in cleaned)


def extract_markdown_section(markdown_body: str, heading: str) -> str:
    pattern = re.compile(rf"^#+\s*{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(markdown_body or "")
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^#+\s+", markdown_body[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(markdown_body)
    return markdown_body[start:end].strip()


def project_approach(project: dict[str, Any]) -> list[str]:
    milestones = project.get("milestones", [])
    approach: list[str] = []
    if isinstance(milestones, list):
        for milestone in milestones:
            if not isinstance(milestone, dict):
                continue
            title = str(milestone.get("title") or "").strip()
            if title:
                approach.append(title)
    return approach


def project_key_outputs(project: dict[str, Any]) -> list[str]:
    outputs = as_list(project.get("deliverables"))
    milestones = project.get("milestones", [])
    if isinstance(milestones, list):
        for milestone in milestones:
            if isinstance(milestone, dict):
                output = str(milestone.get("portfolio_output") or "").strip()
                if output and output not in outputs:
                    outputs.append(output)
    return outputs


def project_chart_prompts(project: dict[str, Any]) -> list[str]:
    prompts: list[str] = []
    for template in project.get("related_portfolio_templates", []):
        if isinstance(template, dict):
            prompt = str(template.get("chart_or_table") or "").strip()
            if prompt:
                prompts.append(prompt)
    return prompts


def project_resume_bullets(project: dict[str, Any]) -> list[str]:
    bullets: list[str] = []
    for template in project.get("related_portfolio_templates", []):
        if isinstance(template, dict):
            bullet = str(template.get("readme_bullet") or "").strip()
            if bullet:
                bullets.append(bullet)
    return bullets


def generate_project_section(project: dict[str, Any]) -> str:
    title = str(project.get("title") or project.get("id") or "Untitled project").strip()
    goal = str(project.get("goal") or "Fill manually.").strip()
    datasets = as_list(project.get("related_dataset_names")) or as_list(project.get("datasets"))
    skills = as_list(project.get("skills"))
    prompt = str(project.get("portfolio_prompt") or "").strip()

    return "\n".join(
        [
            f"## {title}",
            "",
            f"**Goal:** {goal}",
            "",
            "**Datasets used:**",
            markdown_list(datasets, fallback="Add dataset names manually."),
            "",
            "**Skills practiced:**",
            markdown_list(skills, fallback="Add skills manually."),
            "",
            "**Approach:**",
            markdown_list(project_approach(project), fallback="Describe the analysis steps manually."),
            "",
            "**Key outputs:**",
            markdown_list(project_key_outputs(project), fallback="Add real outputs manually after completing the project."),
            "",
            "**Charts/tables to add manually:**",
            markdown_list(project_chart_prompts(project), fallback="Add screenshots or links to charts/tables manually."),
            "",
            "**Limitations:**",
            "- Fill manually: data quality limits, assumptions, missing context, and what this analysis cannot prove.",
            "",
            "**Next steps:**",
            "- Fill manually: the next question, metric, chart, or validation step.",
            "",
            "**Resume bullet draft:**",
            markdown_list(project_resume_bullets(project), fallback="Draft a resume bullet after adding real findings."),
            "",
            "**Portfolio prompt:**",
            prompt or "Fill manually.",
            "",
        ]
    )


def generate_practice_section(card: dict[str, Any], output_record: dict[str, Any] | None = None) -> str:
    title = str(card.get("title") or card.get("id") or "Untitled practice").strip()
    dataset = str(card.get("dataset") or "No dataset").strip()
    practiced = " · ".join(
        item
        for item in [
            str(card.get("section") or "").strip(),
            str(card.get("difficulty") or "").strip(),
            str(card.get("est_time") or "").strip(),
        ]
        if item
    )
    artifact_idea = extract_markdown_section(str(card.get("body") or ""), "Что положить в портфолио")
    record = output_record if isinstance(output_record, dict) else {}
    saved_artifact = str(record.get("artifact") or "").strip()
    saved_summary = str(record.get("summary") or "").strip()

    artifact_lines = []
    if artifact_idea:
        artifact_lines.append(artifact_idea)
    if saved_artifact:
        artifact_lines.append(f"Saved artifact path/link: {saved_artifact}")
    if saved_summary:
        artifact_lines.append(f"Saved note: {saved_summary}")

    return "\n".join(
        [
            f"## {title}",
            "",
            f"**Dataset:** {dataset}",
            "",
            f"**What was practiced:** {practiced or 'Fill manually.'}",
            "",
            "**Artifact idea:**",
            markdown_list(artifact_lines, fallback="Add the artifact idea manually from the practice card."),
            "",
        ]
    )


def generate_portfolio_markdown(
    projects: list[dict[str, Any]],
    practice_cards: list[dict[str, Any]],
    output_records: dict[str, dict[str, Any]] | None = None,
) -> str:
    records = output_records or {}
    lines = [
        "# ML Learning Portfolio",
        "",
        f"> {EXPORT_WARNING}",
        "",
    ]

    if projects:
        lines.extend(["# Data Lab Projects", ""])
        for project in projects:
            lines.append(generate_project_section(project))

    if practice_cards:
        lines.extend(["# Practice Cards", ""])
        for card in practice_cards:
            lines.append(generate_practice_section(card, records.get(str(card.get("id") or ""))))

    if not projects and not practice_cards:
        lines.extend(
            [
                "No completed projects or practice cards were selected.",
                "",
                "Complete learning activities first, then export a portfolio template.",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def portfolio_export_path(portfolio_dir: str | Path) -> Path:
    root = Path(portfolio_dir)
    readme = root / "README.md"
    if readme.exists():
        return root / "generated_portfolio.md"
    return readme
