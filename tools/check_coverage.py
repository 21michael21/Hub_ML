from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "content" / "roadmap" / "coverage_matrix.json"
DEFAULT_OUTPUT_DIR = ROOT / "content" / "reports"
DEFAULT_KNOWN_VAULT = Path("/Users/mihailkulibaba/Projects/practic_ML/obsidian_vkat")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class SourceItem:
    kind: str
    path: str
    title: str
    text: str
    quality_score: int | None = None


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def pattern_hits(text: str, patterns: list[str]) -> list[str]:
    normalized = normalize_text(text)
    hits: list[str] = []
    for pattern in patterns:
        needle = normalize_text(pattern)
        if needle and re.search(rf"(?<![\w+-]){re.escape(needle)}(?![\w+-])", normalized):
            hits.append(pattern)
    return hits


def item_matches(item: SourceItem, patterns: list[str]) -> list[str]:
    return pattern_hits(f"{item.path}\n{item.title}\n{item.text}", patterns)


def evidence_for_patterns(items: list[SourceItem], patterns: list[str], limit: int = 5) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in items:
        hits = item_matches(item, patterns)
        if not hits:
            continue
        evidence.append(
            {
                "kind": item.kind,
                "path": item.path,
                "title": item.title,
                "matched_patterns": hits[:6],
                "quality_score": item.quality_score,
            }
        )
        if len(evidence) >= limit:
            break
    return evidence


def classify_topic_coverage(
    has_theory: bool,
    has_practice: bool,
    has_task: bool,
    has_algorithm: bool,
    has_interview: bool,
    theory_quality: float | None = None,
) -> str:
    practical = has_practice or has_task or has_algorithm or has_interview
    if has_theory and practical:
        if theory_quality is not None and theory_quality < 45:
            return "partial"
        return "covered"
    if has_theory:
        return "theory_only"
    if practical:
        return "practice_only"
    return "missing"


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
    return fields, body


def is_hidden_path(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part.startswith(".") for part in relative.parts)


def title_from_markdown(path: Path, fields: dict[str, Any], body: str) -> str:
    title = str(fields.get("title") or "").strip()
    if title:
        return title
    match = HEADING_RE.search(body)
    if match:
        return match.group(1).strip()
    return path.stem.replace("_", " ").replace("-", " ")


def load_theory_audit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def audit_quality_by_path(audit: dict[str, Any]) -> dict[str, int]:
    quality: dict[str, int] = {}
    for note in audit.get("notes", []):
        if not isinstance(note, dict):
            continue
        relative = str(note.get("relative_path") or "")
        try:
            score = int(note.get("quality_score"))
        except (TypeError, ValueError):
            continue
        if relative:
            quality[relative] = score
    return quality


def resolve_vault(cli_value: str | None, audit: dict[str, Any]) -> Path | None:
    candidates = [
        cli_value,
        os.environ.get("VAULT_PATH"),
        audit.get("vault") if isinstance(audit, dict) else None,
        str(DEFAULT_KNOWN_VAULT),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(str(candidate)).expanduser().resolve()
        if path.exists() and path.is_dir():
            return path
    return None


def load_theory_items(vault: Path | None, audit: dict[str, Any]) -> list[SourceItem]:
    quality = audit_quality_by_path(audit)
    items: list[SourceItem] = []

    if vault is not None:
        for path in sorted(vault.rglob("*.md"), key=lambda item: item.as_posix().casefold()):
            if is_hidden_path(path, vault):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            fields, body = parse_frontmatter(text)
            relative = path.relative_to(vault).as_posix()
            items.append(
                SourceItem(
                    kind="theory",
                    path=relative,
                    title=title_from_markdown(path, fields, body),
                    text=f"{fields}\n{body}",
                    quality_score=quality.get(relative),
                )
            )
        return items

    for note in audit.get("notes", []):
        if not isinstance(note, dict):
            continue
        items.append(
            SourceItem(
                kind="theory",
                path=str(note.get("relative_path") or ""),
                title=str(note.get("title") or ""),
                text=" ".join(
                    str(value)
                    for value in [
                        note.get("relative_path"),
                        note.get("title"),
                        note.get("section"),
                        " ".join(note.get("frontmatter_fields", [])),
                    ]
                    if value
                ),
                quality_score=note.get("quality_score"),
            )
        )
    return items


def load_practice_items(practice_dir: Path) -> list[SourceItem]:
    if not practice_dir.exists():
        return []
    items: list[SourceItem] = []
    for path in sorted(practice_dir.glob("*.md"), key=lambda item: item.name.casefold()):
        text = path.read_text(encoding="utf-8", errors="replace")
        fields, body = parse_frontmatter(text)
        title = str(fields.get("title") or path.stem)
        section = str(fields.get("section") or "")
        dataset = str(fields.get("dataset") or "")
        items.append(
            SourceItem(
                kind="practice",
                path=path.as_posix(),
                title=title,
                text=f"{section}\n{dataset}\n{fields}\n{body}",
            )
        )
    return items


def load_task_items(path: Path) -> list[SourceItem]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items: list[SourceItem] = []
    for task in data.get("tasks", []):
        if not isinstance(task, dict):
            continue
        items.append(
            SourceItem(
                kind="mentor_task",
                path=str(task.get("source_notebook") or task.get("id") or ""),
                title=str(task.get("title") or ""),
                text="\n".join(
                    str(task.get(key) or "")
                    for key in ["source_notebook", "title", "prompt", "starter_code", "tests", "confidence"]
                ),
            )
        )
    return items


def load_algorithm_items(algos_dir: Path) -> list[SourceItem]:
    if not algos_dir.exists():
        return []
    items: list[SourceItem] = []
    for path in sorted(algos_dir.glob("*.py"), key=lambda item: item.name.casefold()):
        text = path.read_text(encoding="utf-8", errors="replace")
        items.append(
            SourceItem(
                kind="algorithm",
                path=path.as_posix(),
                title=path.stem.replace("_", " ").title(),
                text=text[:12000],
            )
        )
    return items


def load_interview_items(path: Path) -> list[SourceItem]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items: list[SourceItem] = []
    for company in data.get("companies", []):
        if not isinstance(company, dict):
            continue
        name = str(company.get("company") or "")
        text = "\n".join(
            str(value)
            for value in [
                name,
                "\n".join(str(item) for item in company.get("questions", [])),
                "\n".join(str(item) for item in company.get("tasks", [])),
                company.get("relevance", ""),
                company.get("notes", ""),
            ]
            if value
        )
        items.append(SourceItem(kind="interview", path=name, title=name, text=text))
    return items


def load_matrix(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    topics = data.get("topics", [])
    if not isinstance(topics, list):
        raise SystemExit(f"Invalid matrix file, expected topics list: {path}")
    return [topic for topic in topics if isinstance(topic, dict)]


def average_quality(evidence: list[dict[str, Any]]) -> float | None:
    scores = [
        float(item["quality_score"])
        for item in evidence
        if isinstance(item.get("quality_score"), int | float)
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def evaluate_topic(
    topic: dict[str, Any],
    theory_items: list[SourceItem],
    practice_items: list[SourceItem],
    task_items: list[SourceItem],
    algorithm_items: list[SourceItem],
    interview_items: list[SourceItem],
) -> dict[str, Any]:
    note_patterns = list(topic.get("expected_note_patterns") or [])
    task_patterns = list(topic.get("expected_task_tags") or [])
    practice_patterns = list(topic.get("expected_practice_patterns") or [])

    theory = evidence_for_patterns(theory_items, note_patterns)
    practice = evidence_for_patterns(practice_items, practice_patterns)
    tasks = evidence_for_patterns(task_items, task_patterns)
    track = str(topic.get("track") or "")
    algorithms = (
        evidence_for_patterns(algorithm_items, task_patterns + note_patterns)
        if track in {"Python", "Interview Prep"}
        else []
    )
    interviews = (
        evidence_for_patterns(interview_items, task_patterns + note_patterns + practice_patterns)
        if track == "Interview Prep"
        else []
    )
    quality = average_quality(theory)
    status = classify_topic_coverage(
        has_theory=bool(theory),
        has_practice=bool(practice),
        has_task=bool(tasks),
        has_algorithm=bool(algorithms),
        has_interview=bool(interviews),
        theory_quality=quality,
    )
    return {
        "id": topic.get("id"),
        "title": topic.get("title"),
        "track": topic.get("track"),
        "level": topic.get("level"),
        "required": bool(topic.get("required")),
        "status": status,
        "theory_quality": quality,
        "evidence_counts": {
            "theory": len(theory),
            "practice": len(practice),
            "mentor_tasks": len(tasks),
            "algorithms": len(algorithms),
            "interviews": len(interviews),
        },
        "evidence": {
            "theory": theory,
            "practice": practice,
            "mentor_tasks": tasks,
            "algorithms": algorithms,
            "interviews": interviews,
        },
        "expected_project_types": topic.get("expected_project_types") or [],
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_track: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        by_track[str(result["track"])][str(result["status"])] += 1

    priority = {"missing": 0, "practice_only": 1, "theory_only": 2, "partial": 3, "covered": 9}
    required_gaps = [
        result
        for result in results
        if result.get("required") and result.get("status") != "covered"
    ]
    required_gaps.sort(
        key=lambda item: (
            priority.get(str(item["status"]), 8),
            str(item["track"]),
            {"beginner": 0, "junior": 1, "middle": 2}.get(str(item["level"]), 9),
            str(item["title"]),
        )
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_topics": len(results),
        "status_counts": dict(Counter(str(result["status"]) for result in results)),
        "coverage_by_track": {track: dict(counter) for track, counter in sorted(by_track.items())},
        "missing_required_topics": [
            compact_topic(result) for result in required_gaps if result["status"] == "missing"
        ],
        "theory_without_practice": [
            compact_topic(result) for result in results if result["status"] == "theory_only"
        ],
        "practice_without_theory": [
            compact_topic(result) for result in results if result["status"] == "practice_only"
        ],
        "recommended_next_10_topics": [compact_topic(result) for result in required_gaps[:10]],
        "recommended_next_3_project_directions": recommended_project_directions(results),
    }


def compact_topic(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": result.get("id"),
        "title": result.get("title"),
        "track": result.get("track"),
        "level": result.get("level"),
        "status": result.get("status"),
    }


def recommended_project_directions(results: list[dict[str, Any]]) -> list[str]:
    status_by_track: dict[str, set[str]] = defaultdict(set)
    for result in results:
        if result.get("status") != "covered":
            status_by_track[str(result.get("track"))].add(str(result.get("status")))

    directions: list[str] = []
    if status_by_track.get("Data Analysis") or status_by_track.get("Statistics"):
        directions.append(
            "EDA + visualization case study on df_orders/df_events: data quality, metrics, charts, and written business insights."
        )
    if status_by_track.get("Classic ML") or status_by_track.get("Math for ML"):
        directions.append(
            "Classic ML baseline project: supervised model, validation split, metrics, error analysis, and reproducible README."
        )
    if status_by_track.get("NLP") or status_by_track.get("GenAI and RAG"):
        directions.append(
            "NLP/RAG portfolio prototype: text preprocessing or retrieval baseline with clear evaluation notes."
        )
    if len(directions) < 3 and status_by_track.get("MLOps"):
        directions.append(
            "MLOps mini-project: experiment log, saved artifacts, batch inference script, and monitoring checklist."
        )
    if len(directions) < 3:
        directions.append(
            "Interview readiness pack: solved algorithm lessons, ML/DS answer bank, and take-home postmortem."
        )
    return directions[:3]


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def build_markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    results = payload["topics"]
    track_rows = []
    for track, counts in summary["coverage_by_track"].items():
        total = sum(counts.values())
        track_rows.append(
            [
                track,
                total,
                counts.get("covered", 0),
                counts.get("partial", 0),
                counts.get("theory_only", 0),
                counts.get("practice_only", 0),
                counts.get("missing", 0),
            ]
        )

    missing_rows = [
        [item["track"], item["level"], item["id"], item["title"], item["status"]]
        for item in summary["missing_required_topics"]
    ]
    theory_only_rows = [
        [item["track"], item["level"], item["id"], item["title"]]
        for item in summary["theory_without_practice"]
    ]
    practice_only_rows = [
        [item["track"], item["level"], item["id"], item["title"]]
        for item in summary["practice_without_theory"]
    ]
    next_rows = [
        [index + 1, item["track"], item["level"], item["id"], item["title"], item["status"]]
        for index, item in enumerate(summary["recommended_next_10_topics"])
    ]

    return "\n".join(
        [
            "# Learning Coverage Report",
            "",
            f"Generated: `{summary['generated_at']}`",
            f"Vault: `{payload.get('vault') or 'not available'}`",
            "",
            "## Summary",
            "",
            f"- Total topics: **{summary['total_topics']}**",
            f"- Status counts: `{summary['status_counts']}`",
            "",
            "## Overall Coverage By Track",
            "",
            markdown_table(
                ["Track", "Total", "Covered", "Partial", "Theory Only", "Practice Only", "Missing"],
                track_rows,
            ),
            "",
            "## Missing Required Topics",
            "",
            markdown_table(["Track", "Level", "ID", "Title", "Status"], missing_rows)
            if missing_rows
            else "_No missing required topics._",
            "",
            "## Theory Without Practice",
            "",
            markdown_table(["Track", "Level", "ID", "Title"], theory_only_rows)
            if theory_only_rows
            else "_No theory-only topics._",
            "",
            "## Practice Without Theory",
            "",
            markdown_table(["Track", "Level", "ID", "Title"], practice_only_rows)
            if practice_only_rows
            else "_No practice-only topics._",
            "",
            "## Recommended Next 10 Topics To Fix",
            "",
            markdown_table(["#", "Track", "Level", "ID", "Title", "Status"], next_rows)
            if next_rows
            else "_No required gaps detected._",
            "",
            "## Recommended Next 3 Project Directions",
            "",
            "\n".join(
                f"{index + 1}. {direction}"
                for index, direction in enumerate(summary["recommended_next_3_project_directions"])
            ),
            "",
            "## Topic Details",
            "",
            "\n".join(topic_detail_markdown(result) for result in results),
            "",
        ]
    )


def topic_detail_markdown(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    lines = [
        f"### {result['title']}",
        "",
        f"- ID: `{result['id']}`",
        f"- Track: `{result['track']}`",
        f"- Level: `{result['level']}`",
        f"- Required: `{result['required']}`",
        f"- Status: **{result['status']}**",
        f"- Theory quality: `{result['theory_quality']}`",
    ]
    for key, label in [
        ("theory", "Theory"),
        ("practice", "Practice"),
        ("mentor_tasks", "Mentor Tasks"),
        ("algorithms", "Algorithms"),
        ("interviews", "Interviews"),
    ]:
        items = evidence.get(key) or []
        if not items:
            continue
        lines.append(f"- {label}: " + "; ".join(f"`{item['path']}`" for item in items[:3]))
    return "\n".join(lines)


def build_coverage_payload(args: argparse.Namespace) -> dict[str, Any]:
    audit_path = ROOT / "content" / "reports" / "theory_audit.json"
    audit = load_theory_audit(audit_path)
    vault = resolve_vault(args.vault, audit)
    topics = load_matrix(Path(args.matrix))
    theory_items = load_theory_items(vault, audit)
    practice_items = load_practice_items(ROOT / "practice")
    task_items = load_task_items(ROOT / "content" / "extracted" / "mentor_tasks.json")
    algorithm_items = load_algorithm_items(ROOT / "content" / "source" / "vkat" / "VKAT-main" / "algos_patterns")
    interview_items = load_interview_items(ROOT / "content" / "interview_questions" / "ml_ds_interview_questions.json")

    results = [
        evaluate_topic(topic, theory_items, practice_items, task_items, algorithm_items, interview_items)
        for topic in topics
    ]
    summary = summarize_results(results)
    return {
        "vault": str(vault) if vault else None,
        "sources": {
            "theory_notes": len(theory_items),
            "practice_cards": len(practice_items),
            "mentor_tasks": len(task_items),
            "algorithm_lessons": len(algorithm_items),
            "interview_companies": len(interview_items),
            "theory_audit": str(audit_path) if audit else None,
        },
        "summary": summary,
        "topics": results,
    }


def write_reports(payload: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "coverage_report.json"
    md_path = output_dir / "coverage_report.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown_report(payload), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Hub_ML learning coverage against a roadmap matrix.")
    parser.add_argument("--vault", help="Path to the Obsidian vault. Defaults to VAULT_PATH, audit report vault, or known local path.")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), help="Coverage matrix JSON path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for coverage_report.json/md.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing report files.")
    args = parser.parse_args()

    payload = build_coverage_payload(args)
    summary = payload["summary"]
    print(f"Vault: {payload.get('vault') or 'not available'}")
    print(f"Total topics: {summary['total_topics']}")
    print(f"Status counts: {summary['status_counts']}")
    print("Coverage by track:")
    for track, counts in summary["coverage_by_track"].items():
        print(f"  - {track}: {counts}")

    if args.dry_run:
        return

    json_path, md_path = write_reports(payload, Path(args.output_dir))
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
