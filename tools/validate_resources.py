from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESOURCES = ROOT / "content" / "resources" / "ml_ds_resources.json"
DEFAULT_MATRIX = ROOT / "content" / "roadmap" / "coverage_matrix.json"

REQUIRED_FIELDS = ("id", "title", "track", "type", "language", "cost", "url")
ENUMS = {
    "type": {"course", "guide", "book", "interactive", "video", "paper", "docs", "cheatsheet"},
    "language": {"en", "ru", "multi"},
    "level": {"beginner", "junior", "intermediate", "advanced"},
    "cost": {"free", "freemium", "paid"},
    "access": {"open", "signup", "trial"},
    "priority": {"core", "support", "deep_dive", "later"},
    "status": {"active", "stale"},
}
PLACEHOLDER_MARKERS = ("example.com", "todo", "<", "xxx")
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_coverage_tracks(matrix_path: str | Path = DEFAULT_MATRIX) -> set[str]:
    matrix = load_json(matrix_path)
    topics = matrix.get("topics", []) if isinstance(matrix, dict) else []
    return {str(topic.get("track")) for topic in topics if isinstance(topic, dict) and topic.get("track")}


def resource_identifier(record: Any, index: int) -> str:
    if isinstance(record, dict) and str(record.get("id") or "").strip():
        return str(record["id"]).strip()
    return f"record[{index}]"


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def validate_url(url: str) -> list[str]:
    errors: list[str] = []
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append("url must be an http(s) URL")
    lowered = url.casefold()
    for marker in PLACEHOLDER_MARKERS:
        if marker in lowered:
            errors.append(f"url contains placeholder marker '{marker}'")
    return errors


def validate_resource_record(
    record: Any,
    *,
    index: int,
    seen_ids: set[str],
    valid_tracks: set[str],
) -> list[str]:
    resource_id = resource_identifier(record, index)
    if not isinstance(record, dict):
        return [f"FAIL {resource_id}: record must be an object"]

    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record or is_empty(record.get(field)):
            errors.append(f"FAIL {resource_id}: missing required field '{field}'")

    raw_id = str(record.get("id") or "").strip()
    if raw_id:
        if raw_id in seen_ids:
            errors.append(f"FAIL {resource_id}: duplicate id '{raw_id}'")
        if not SNAKE_CASE_RE.match(raw_id):
            errors.append(f"FAIL {resource_id}: id must be a snake_case slug")
        seen_ids.add(raw_id)

    track = str(record.get("track") or "").strip()
    if track and track not in valid_tracks:
        errors.append(f"FAIL {resource_id}: track '{track}' not in coverage_matrix")

    for field, allowed in ENUMS.items():
        value = record.get(field)
        if is_empty(value):
            continue
        text = str(value).strip()
        if text not in allowed:
            allowed_text = ",".join(sorted(allowed))
            errors.append(f"FAIL {resource_id}: {field} '{text}' not in {{{allowed_text}}}")

    url = str(record.get("url") or "").strip()
    if url:
        errors.extend(f"FAIL {resource_id}: {message}" for message in validate_url(url))

    for list_field in ("related_hubml_modules", "expected_output"):
        value = record.get(list_field)
        if value is not None and not isinstance(value, list):
            errors.append(f"FAIL {resource_id}: {list_field} must be a list")

    return errors


def validate_resources(records: Any, valid_tracks: set[str]) -> list[str]:
    if not isinstance(records, list):
        return ["FAIL registry: top-level JSON must be a list"]
    seen_ids: set[str] = set()
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(
            validate_resource_record(
                record,
                index=index,
                seen_ids=seen_ids,
                valid_tracks=valid_tracks,
            )
        )
    return errors


def validation_summary(records: list[dict[str, Any]]) -> str:
    tracks = {str(record.get("track")) for record in records if isinstance(record, dict) and record.get("track")}
    return f"resources OK: {len(records)} records, {len(tracks)} tracks covered"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate curated Hub_ML resource registry.")
    parser.add_argument("--resources", default=str(DEFAULT_RESOURCES), help="Path to ml_ds_resources.json")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), help="Path to coverage_matrix.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        records = load_json(args.resources)
        valid_tracks = load_coverage_tracks(args.matrix)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL registry: {exc}", file=sys.stderr)
        return 1

    errors = validate_resources(records, valid_tracks)
    if errors:
        print("\n".join(errors))
        return 1

    print(validation_summary(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
