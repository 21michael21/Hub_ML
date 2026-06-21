from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "content" / "roadmap" / "coverage_matrix.json"
DEFAULT_AUDIT = ROOT / "content" / "reports" / "theory_audit.json"
DEFAULT_RESOURCES = ROOT / "content" / "resources" / "ml_ds_resources.json"
DEFAULT_PRACTICE_DIR = ROOT / "practice"
DEFAULT_TASKS = ROOT / "content" / "extracted" / "mentor_tasks.json"
DEFAULT_OUTPUT_DIR = ROOT / "content" / "reports"
URL_RE = re.compile(r"https?://[^\s)>\"]+")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def pattern_hits(text: str, patterns: list[str]) -> list[str]:
    normalized = normalize_text(text)
    hits: list[str] = []
    for pattern in patterns:
        needle = normalize_text(pattern)
        if needle and re.search(rf"(?<![\w+-]){re.escape(needle)}(?![\w+-])", normalized):
            hits.append(str(pattern))
    return hits


def matches_topic_patterns(text: str, patterns: list[str]) -> bool:
    hits = pattern_hits(text, patterns)
    required_hits = 1 if len(patterns) <= 1 else 2
    return len(hits) >= required_hits


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


def item_text(item: dict[str, Any]) -> str:
    return "\n".join(str(item.get(key) or "") for key in ("id", "path", "title", "text"))


def note_text(note: dict[str, Any]) -> str:
    return "\n".join(
        str(note.get(key) or "")
        for key in ("relative_path", "section", "title", "frontmatter_fields")
    )


def matching_notes(topic: dict[str, Any], notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns = list(topic.get("expected_note_patterns") or [])
    return [note for note in notes if matches_topic_patterns(note_text(note), patterns)]


def matching_items(topic: dict[str, Any], items: list[dict[str, Any]], patterns_key: str) -> list[dict[str, Any]]:
    patterns = list(topic.get(patterns_key) or [])
    return [item for item in items if matches_topic_patterns(item_text(item), patterns)]


def registered_urls(resources: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("url")).strip() for item in resources if isinstance(item, dict) and str(item.get("url") or "").strip()}


def extract_urls(text: str) -> list[str]:
    return [match.group(0).rstrip(".,;:!?]") for match in URL_RE.finditer(text)]


def read_note_body(vault: Path | None, relative_path: str) -> str:
    if not vault or not relative_path:
        return ""
    path = (vault / relative_path).resolve()
    try:
        path.relative_to(vault.resolve())
    except ValueError:
        return ""
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    _, body = parse_frontmatter(text)
    return body


def note_registered_urls(note: dict[str, Any], vault: Path | None, allowed_urls: set[str]) -> set[str]:
    body = read_note_body(vault, str(note.get("relative_path") or ""))
    return {url for url in extract_urls(body) if url in allowed_urls}


def score(note: dict[str, Any]) -> int:
    try:
        return int(note.get("quality_score") or 0)
    except (TypeError, ValueError):
        return 0


def evaluate_topic_gate(
    topic: dict[str, Any],
    *,
    notes: list[dict[str, Any]],
    vault: Path | None,
    registered_urls: set[str],
    practice_items: list[dict[str, Any]],
    task_items: list[dict[str, Any]],
    threshold: int,
) -> dict[str, Any]:
    candidates = sorted(matching_notes(topic, notes), key=score, reverse=True)
    quality_notes = [note for note in candidates if score(note) >= threshold]
    clean_notes = [note for note in quality_notes if not bool(note.get("likely_ai_dump_or_placeholder"))]
    sourced_notes: list[tuple[dict[str, Any], set[str]]] = []
    for note in clean_notes:
        urls = note_registered_urls(note, vault, registered_urls)
        if bool(note.get("has_sources_section")) and urls:
            sourced_notes.append((note, urls))

    practice = matching_items(topic, practice_items, "expected_practice_patterns")
    tasks = [
        item for item in matching_items(topic, task_items, "expected_task_tags")
        if bool(item.get("has_asserts"))
    ]

    best_score = score(candidates[0]) if candidates else 0
    best_ai_flag = bool(quality_notes[0].get("likely_ai_dump_or_placeholder")) if quality_notes else None
    best_source_note = clean_notes[0] if clean_notes else None
    registered_count = len(note_registered_urls(best_source_note, vault, registered_urls)) if best_source_note else 0
    has_sources_header = bool(best_source_note and best_source_note.get("has_sources_section"))
    if not quality_notes:
        rule2_detail = "no qualified note"
    elif clean_notes:
        rule2_detail = "ai_dump_flag false"
    else:
        rule2_detail = "ai_dump_flag true"
    if clean_notes:
        rule3_detail = (
            f"{len(sourced_notes[0][1])} registered URLs"
            if sourced_notes
            else f"header {'present' if has_sources_header else 'missing'}, {registered_count} registered URLs"
        )
    else:
        rule3_detail = "blocked by rule1/rule2"

    rules = {
        "rule1_note_quality": {
            "passed": bool(quality_notes),
            "detail": f"{best_score} >= {threshold}" if quality_notes else f"{best_score} < {threshold}",
            "best_score": best_score,
            "threshold": threshold,
            "matched_notes": len(candidates),
        },
        "rule2_ai_dump_flag": {
            "passed": bool(clean_notes),
            "detail": rule2_detail,
            "ai_dump_flag": best_ai_flag,
        },
        "rule3_sources": {
            "passed": bool(sourced_notes),
            "detail": rule3_detail,
            "registered_url_count": len(sourced_notes[0][1]) if sourced_notes else registered_count,
            "has_sources_section": has_sources_header,
        },
        "rule4_practice_or_task": {
            "passed": bool(practice or tasks),
            "detail": f"{len(practice)} practice, {len(tasks)} task",
            "practice_count": len(practice),
            "task_count": len(tasks),
        },
    }
    failed = [key.replace("_note_quality", "").replace("_ai_dump_flag", "").replace("_sources", "").replace("_practice_or_task", "") for key, rule in rules.items() if not rule["passed"]]
    return {
        "id": topic.get("id"),
        "title": topic.get("title"),
        "track": topic.get("track"),
        "required": bool(topic.get("required")),
        "status": "PASS" if not failed else "FAIL",
        "failed_rules": failed,
        "rules": rules,
        "evidence": {
            "notes": [{"path": note.get("relative_path"), "title": note.get("title"), "quality_score": score(note)} for note in candidates[:5]],
            "practice": [{"id": item.get("id"), "title": item.get("title")} for item in practice[:5]],
            "tasks": [{"id": item.get("id"), "title": item.get("title")} for item in tasks[:5]],
        },
    }


def load_matrix(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    topics = data.get("topics", []) if isinstance(data, dict) else []
    return [topic for topic in topics if isinstance(topic, dict)]


def filter_topics(topics: list[dict[str, Any]], topic_id: str | None) -> list[dict[str, Any]]:
    if not topic_id:
        return topics
    selected = [topic for topic in topics if str(topic.get("id") or "") == topic_id]
    if not selected:
        raise SystemExit(f"Topic not found: {topic_id}")
    return selected


def load_practice_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for card in sorted(path.glob("*.md"), key=lambda item: item.name.casefold()):
        text = card.read_text(encoding="utf-8", errors="replace")
        fields, body = parse_frontmatter(text)
        items.append(
            {
                "id": card.stem,
                "path": card.as_posix(),
                "title": fields.get("title") or card.stem,
                "text": f"{fields}\n{body}",
            }
        )
    return items


def load_task_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_json(path)
    items: list[dict[str, Any]] = []
    for task in data.get("tasks", []) if isinstance(data, dict) else []:
        if not isinstance(task, dict):
            continue
        items.append(
            {
                "id": task.get("id"),
                "path": task.get("source_notebook") or task.get("source_path"),
                "title": task.get("title"),
                "has_asserts": bool(task.get("has_asserts")),
                "text": "\n".join(str(task.get(key) or "") for key in ("source_notebook", "title", "prompt", "starter_code", "tests")),
            }
        )
    return items


def build_content_gate_payload(
    *,
    topics: list[dict[str, Any]],
    audit: dict[str, Any],
    resources: list[dict[str, Any]],
    practice_items: list[dict[str, Any]],
    task_items: list[dict[str, Any]],
    threshold: int,
) -> dict[str, Any]:
    vault_value = audit.get("vault") if isinstance(audit, dict) else None
    vault = Path(str(vault_value)).expanduser().resolve() if vault_value else None
    if vault and not vault.exists():
        vault = None
    notes = [note for note in audit.get("notes", []) if isinstance(note, dict)] if isinstance(audit, dict) else []
    allowed_urls = registered_urls(resources)
    results = [
        evaluate_topic_gate(
            topic,
            notes=notes,
            vault=vault,
            registered_urls=allowed_urls,
            practice_items=practice_items,
            task_items=task_items,
            threshold=threshold,
        )
        for topic in topics
    ]
    failed_rule_counts = Counter(rule for result in results for rule in result["failed_rules"])
    passed = sum(1 for result in results if result["status"] == "PASS")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "vault": str(vault) if vault else None,
        "summary": {
            "total_topics": len(results),
            "passed_topics": passed,
            "failed_topics": len(results) - passed,
            "failed_rule_counts": dict(sorted(failed_rule_counts.items())),
            "failed_required_topic_ids": [str(result["id"]) for result in results if result["required"] and result["status"] == "FAIL"],
        },
        "topics": results,
    }


def rule_mark(passed: bool) -> str:
    return "✓" if passed else "✗"


def build_markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Content Quality Gate Report",
        "",
        f"Generated: `{payload['generated_at']}`",
        f"Threshold: `{payload['threshold']}`",
        f"Vault: `{payload.get('vault') or 'not available'}`",
        "",
        f"Summary: **GATE: {summary['passed_topics']}/{summary['total_topics']} pass, {summary['failed_topics']} fail**",
        f"- Failed rule counts: `{summary['failed_rule_counts']}`",
        "",
    ]
    for topic in payload["topics"]:
        lines.extend([f"## {topic['id']} — {topic['title']}  [{topic['status']}]", ""])
        rule1 = topic["rules"]["rule1_note_quality"]
        rule2 = topic["rules"]["rule2_ai_dump_flag"]
        rule3 = topic["rules"]["rule3_sources"]
        rule4 = topic["rules"]["rule4_practice_or_task"]
        lines.extend(
            [
                f"- rule1 note quality: {rule1['detail']} {rule_mark(rule1['passed'])}",
                f"- rule2 ai_dump_flag: {rule2['detail']} {rule_mark(rule2['passed'])}",
                f"- rule3 sources: {rule3['detail']} {rule_mark(rule3['passed'])}",
                f"- rule4 practice/task: {rule4['detail']} {rule_mark(rule4['passed'])}",
                "",
            ]
        )
    return "\n".join(lines)


def write_reports(payload: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "content_gate_report.json"
    md_path = output_dir / "content_gate_report.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown_report(payload), encoding="utf-8")
    return json_path, md_path


def run_reaudit(vault: str | None) -> None:
    command = [sys.executable, str(ROOT / "tools" / "audit_theory_notes.py")]
    if vault:
        command.extend(["--vault", vault])
    subprocess.run(command, cwd=ROOT, check=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check topic-level Hub_ML content Definition-of-Done.")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--resources", default=str(DEFAULT_RESOURCES))
    parser.add_argument("--practice-dir", default=str(DEFAULT_PRACTICE_DIR))
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--threshold", type=int, default=70)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--reaudit", action="store_true")
    parser.add_argument("--vault", default=os.environ.get("VAULT_PATH"))
    parser.add_argument("--topic", help="Optional coverage topic id to evaluate.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.reaudit:
        run_reaudit(args.vault)

    topics = filter_topics(load_matrix(Path(args.matrix)), args.topic)
    audit = load_json(args.audit)
    resources = load_json(args.resources)
    practice_items = load_practice_items(Path(args.practice_dir))
    task_items = load_task_items(Path(args.tasks))
    payload = build_content_gate_payload(
        topics=topics,
        audit=audit if isinstance(audit, dict) else {},
        resources=resources if isinstance(resources, list) else [],
        practice_items=practice_items,
        task_items=task_items,
        threshold=args.threshold,
    )
    json_path, md_path = write_reports(payload, Path(args.output_dir))
    summary = payload["summary"]
    print(f"GATE: {summary['passed_topics']}/{summary['total_topics']} pass, {summary['failed_topics']} fail")
    print(f"Failed rule counts: {summary['failed_rule_counts']}")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    if args.strict and summary["failed_required_topic_ids"]:
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
