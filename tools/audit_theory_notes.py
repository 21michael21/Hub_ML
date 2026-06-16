from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WIKILINK_RE = re.compile(r"\[\[([^\]\n]+?)\]\]")
EXTERNAL_LINK_RE = re.compile(r"(?<![!])\[[^\]]+\]\((https?://[^)]+)\)|https?://[^\s)>\"]+")
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_+-]+")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)

TECH_TOPIC_RE = re.compile(
    r"\b("
    r"python|pandas|numpy|sklearn|scikit|matplotlib|seaborn|sql|api|git|docker|"
    r"model|models|ml|machine learning|nlp|llm|rag|embedding|token|dataset|"
    r"feature|metric|classification|regression|clustering|statistics|stats|"
    r"визуал|график|датасет|модель|метрик|классификац|регресси|статист"
    r")\b",
    re.IGNORECASE,
)

GENERIC_HEADING_RE = re.compile(
    r"^(overview|summary|intro|introduction|notes|todo|draft|basics|"
    r"обзор|введение|заметки|итог|кратко|основы|черновик|todo)$",
    re.IGNORECASE,
)

CORE_TOPICS = {
    "Python basics": ("python", "list", "dict", "function", "class", "ооп", "функц"),
    "NumPy": ("numpy", "array", "ndarray"),
    "Pandas": ("pandas", "dataframe", "groupby", "merge"),
    "Statistics": ("statistics", "stats", "статист", "distribution", "hypothesis"),
    "Data visualization": ("visualization", "matplotlib", "seaborn", "график", "визуал"),
    "Machine learning": ("machine learning", "ml", "model", "модель"),
    "Model evaluation": ("metric", "evaluation", "precision", "recall", "auc", "валидац"),
    "Feature engineering": ("feature", "признак", "encoding"),
    "NLP": ("nlp", "token", "text", "transformer", "текст"),
    "LLM / prompting": ("llm", "prompt", "rag", "embedding", "agent"),
    "SQL": ("sql", "join", "window function"),
    "Git": ("git", "commit", "branch"),
    "Portfolio": ("portfolio", "портфолио", "case study"),
}


def is_hidden_path(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part.startswith(".") for part in relative.parts)


def humanize_section(name: str) -> str:
    return " ".join(part.capitalize() for part in name.replace("_", " ").split()) or "Без раздела"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, bool]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text, False

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
        key = key.strip()
        value = value.strip()
        current_key = key
        if not value:
            fields[key] = []
        elif value.startswith("[") and value.endswith("]"):
            fields[key] = [
                item.strip().strip("\"'")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            fields[key] = value.strip().strip("\"'")
    return fields, body, True


def word_count(markdown: str) -> int:
    text = CODE_BLOCK_RE.sub(" ", markdown)
    return len(WORD_RE.findall(text))


def count_tags(frontmatter: dict[str, Any], body: str) -> int:
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tag_count = len([item for item in re.split(r"[,\s]+", tags) if item.strip()])
    elif isinstance(tags, list):
        tag_count = len([item for item in tags if str(item).strip()])
    else:
        tag_count = 0
    inline_tags = set(re.findall(r"(?<!\w)#([A-Za-zА-Яа-яЁё0-9_/-]+)", body))
    return tag_count + len(inline_tags)


def has_heading(markdown: str, patterns: tuple[str, ...]) -> bool:
    for _, heading in HEADING_RE.findall(markdown):
        normalized = heading.strip().strip("#").casefold()
        if any(pattern in normalized for pattern in patterns):
            return True
    return False


def has_examples(markdown: str) -> bool:
    if CODE_BLOCK_RE.search(markdown):
        return True
    return bool(re.search(r"\b(example|examples|например|пример)\b", markdown, re.IGNORECASE))


def section_for_file(path: Path, vault: Path) -> str:
    relative = path.relative_to(vault)
    if len(relative.parts) <= 1:
        return "Без раздела"
    return humanize_section(relative.parts[0])


def title_for_note(path: Path, frontmatter: dict[str, Any], body: str) -> str:
    title = str(frontmatter.get("title", "")).strip()
    if title:
        return title
    match = HEADING_RE.search(body)
    if match:
        return match.group(2).strip()
    return path.stem.replace("_", " ").replace("-", " ").strip()


def generic_heading_ratio(body: str, words: int) -> tuple[int, float]:
    headings = [heading.strip().strip("#") for _, heading in HEADING_RE.findall(body)]
    generic = sum(1 for heading in headings if GENERIC_HEADING_RE.match(heading))
    words_per_heading = words / max(len(headings), 1)
    return generic, words_per_heading


def score_note(metrics: dict[str, Any]) -> int:
    score = 100
    if metrics["word_count"] < 250:
        score -= 25
    if metrics["word_count"] < 80:
        score -= 20
    if metrics["heading_count"] == 0:
        score -= 15
    if metrics["is_technical_topic"] and metrics["code_block_count"] == 0:
        score -= 15
    if not metrics["has_examples"]:
        score -= 10
    if not metrics["has_sources_section"] and metrics["external_link_count"] == 0:
        score -= 10
    if not metrics["has_practice_section"]:
        score -= 5
    if metrics["likely_ai_dump_or_placeholder"]:
        score -= 20
    if not metrics["frontmatter_fields"]:
        score -= 5
    return max(0, min(100, score))


def audit_note(path: Path, vault: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body, has_frontmatter = parse_frontmatter(text)
    words = word_count(body)
    headings = HEADING_RE.findall(body)
    generic_headings, words_per_heading = generic_heading_ratio(body, words)
    wiki_links = WIKILINK_RE.findall(body)
    external_link_count = sum(1 for _ in EXTERNAL_LINK_RE.finditer(body))
    body_stripped = body.strip()
    is_technical = bool(TECH_TOPIC_RE.search(" ".join([str(path), body[:1200]])))
    placeholder = words < 40 and (
        not body_stripped
        or bool(re.fullmatch(r"(?is)\s*(todo|tbd|draft|черновик|coming soon|wip|# .+)?\s*", body_stripped))
    )
    generic_dump = len(headings) >= 5 and words_per_heading < 45

    metrics: dict[str, Any] = {
        "relative_path": path.relative_to(vault).as_posix(),
        "section": section_for_file(path, vault),
        "title": title_for_note(path, frontmatter, body),
        "frontmatter_fields": sorted(frontmatter.keys()),
        "has_frontmatter": has_frontmatter,
        "word_count": words,
        "heading_count": len(headings),
        "code_block_count": len(CODE_BLOCK_RE.findall(body)),
        "wiki_link_count": len(wiki_links),
        "external_link_count": external_link_count,
        "tag_count": count_tags(frontmatter, body),
        "has_examples": has_examples(body),
        "has_practice_section": has_heading(body, ("practice", "практи", "задани", "exercise", "task")),
        "has_sources_section": has_heading(body, ("source", "sources", "reference", "references", "ссыл", "источник", "ресурс")),
        "has_portfolio_section": has_heading(body, ("portfolio", "портфолио", "artifact", "артефакт")),
        "has_prerequisites": has_heading(body, ("prerequisite", "prerequisites", "before", "предвар", "перед тем", "нужно знать")),
        "likely_thin_note": words < 250,
        "likely_ai_dump_or_placeholder": bool(placeholder or generic_dump),
        "is_technical_topic": is_technical,
        "generic_heading_count": generic_headings,
        "words_per_heading": round(words_per_heading, 1),
    }
    metrics["quality_score"] = score_note(metrics)
    return metrics


def scan_vault(vault: Path) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for path in sorted(vault.rglob("*.md"), key=lambda item: item.relative_to(vault).as_posix().casefold()):
        if is_hidden_path(path, vault):
            continue
        notes.append(audit_note(path, vault))
    return notes


def missing_core_topics(notes: list[dict[str, Any]]) -> list[str]:
    haystack = "\n".join(
        f"{note['relative_path']} {note['title']} {note['section']}"
        for note in notes
    ).casefold()
    missing: list[str] = []
    for topic, needles in CORE_TOPICS.items():
        if not any(needle.casefold() in haystack for needle in needles):
            missing.append(topic)
    return missing


def build_summary(notes: list[dict[str, Any]]) -> dict[str, Any]:
    section_counts = Counter(note["section"] for note in notes)
    average = round(sum(note["quality_score"] for note in notes) / len(notes), 1) if notes else 0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_notes": len(notes),
        "notes_by_section": dict(sorted(section_counts.items())),
        "average_quality_score": average,
        "missing_core_topics": missing_core_topics(notes),
        "notes_without_frontmatter": [note["relative_path"] for note in notes if not note["has_frontmatter"]],
        "notes_without_examples": [note["relative_path"] for note in notes if not note["has_examples"]],
        "notes_without_sources": [
            note["relative_path"]
            for note in notes
            if not note["has_sources_section"] and note["external_link_count"] == 0
        ],
        "weakest_notes": sorted(notes, key=lambda note: (note["quality_score"], note["word_count"]))[:20],
    }


def recommended_actions(summary: dict[str, Any]) -> list[str]:
    actions = [
        "Review the top 20 weakest notes first and decide which notes deserve expansion.",
        "Add examples/code snippets to technical notes that currently have no examples.",
        "Add source/reference sections to notes that are copied, AI-generated, or important for interviews.",
        "Add practice and portfolio sections to notes that should become job-ready learning material.",
    ]
    if summary["missing_core_topics"]:
        actions.append("Create or connect missing core topics: " + ", ".join(summary["missing_core_topics"]) + ".")
    if summary["notes_without_frontmatter"]:
        actions.append("Normalize frontmatter for notes without metadata: title, tags, status, source.")
    return actions


def markdown_table(rows: list[list[Any]], headers: list[str]) -> str:
    table = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        table.append("| " + " | ".join(str(item).replace("|", "\\|") for item in row) + " |")
    return "\n".join(table)


def build_markdown_report(vault: Path, notes: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    weakest_rows = [
        [
            note["quality_score"],
            note["word_count"],
            note["section"],
            note["relative_path"],
            note["title"],
        ]
        for note in summary["weakest_notes"]
    ]
    section_rows = [[section, count] for section, count in summary["notes_by_section"].items()]
    actions = recommended_actions(summary)
    without_frontmatter = summary["notes_without_frontmatter"][:50]
    without_examples = summary["notes_without_examples"][:50]
    without_sources = summary["notes_without_sources"][:50]

    return "\n".join(
        [
            "# Theory Content Audit",
            "",
            f"Vault: `{vault}`",
            f"Generated: `{summary['generated_at']}`",
            "",
            "## Summary",
            "",
            f"- Total notes: **{summary['total_notes']}**",
            f"- Average quality score: **{summary['average_quality_score']} / 100**",
            "",
            "## Notes By Section",
            "",
            markdown_table(section_rows, ["Section", "Notes"]) if section_rows else "_No notes found._",
            "",
            "## Top 20 Weakest Notes",
            "",
            markdown_table(weakest_rows, ["Score", "Words", "Section", "Path", "Title"]) if weakest_rows else "_No weak notes found._",
            "",
            "## Missing Core Topics",
            "",
            "\n".join(f"- {topic}" for topic in summary["missing_core_topics"]) or "_No missing core topics detected by filename/title heuristics._",
            "",
            "## Notes Without Frontmatter",
            "",
            "\n".join(f"- `{path}`" for path in without_frontmatter) or "_None._",
            "",
            "## Notes Without Examples",
            "",
            "\n".join(f"- `{path}`" for path in without_examples) or "_None._",
            "",
            "## Notes Without Sources",
            "",
            "\n".join(f"- `{path}`" for path in without_sources) or "_None._",
            "",
            "## Recommended Next Actions",
            "",
            "\n".join(f"- {action}" for action in actions),
            "",
            "## Heuristic Notes",
            "",
            "- `word_count < 250` marks a note as likely thin.",
            "- Technical notes without code blocks are flagged as likely missing examples.",
            "- Notes without source headings or external links are treated as weakly sourced.",
            "- Many generic headings with little content are treated as possible AI dumps.",
            "- Placeholder detection is conservative and based on very short body text.",
            "",
        ]
    )


def write_reports(vault: Path, notes: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(notes)
    payload = {"vault": str(vault), "summary": summary, "notes": notes}
    json_path = output_dir / "theory_audit.json"
    md_path = output_dir / "theory_audit.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown_report(vault, notes, summary), encoding="utf-8")
    return json_path, md_path


def resolve_vault(cli_value: str | None) -> Path:
    vault_value = cli_value or os.environ.get("VAULT_PATH", "")
    if not vault_value.strip():
        raise SystemExit("Provide --vault or set VAULT_PATH.")
    vault = Path(vault_value).expanduser().resolve()
    if not vault.exists() or not vault.is_dir():
        raise SystemExit(f"Vault path does not exist or is not a directory: {vault}")
    return vault


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Obsidian theory markdown notes.")
    parser.add_argument("--vault", help="Path to Obsidian vault. Defaults to VAULT_PATH env var.")
    parser.add_argument("--output-dir", default="content/reports", help="Directory for theory_audit.json/md.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing report files.")
    args = parser.parse_args()

    vault = resolve_vault(args.vault)
    notes = scan_vault(vault)
    summary = build_summary(notes)

    print(f"Vault: {vault}")
    print(f"Total notes: {summary['total_notes']}")
    print(f"Average quality score: {summary['average_quality_score']} / 100")
    print("Notes by section:")
    for section, count in summary["notes_by_section"].items():
        print(f"  - {section}: {count}")
    print(f"Weakest notes reported: {len(summary['weakest_notes'])}")

    if args.dry_run:
        return

    json_path, md_path = write_reports(vault, notes, Path(args.output_dir))
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
