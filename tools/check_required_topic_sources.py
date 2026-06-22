from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESOURCES = ROOT / "content" / "resources" / "ml_ds_resources.json"

REQUIRED_TOPIC_SOURCES: dict[str, set[str]] = {
    "interview.ml_ds_questions": {"ml_interviews_book"},
    "interview.coding": {"tech_interview_handbook", "tech_interview_coding_prep"},
    "interview.take_home": {
        "ml_interviews_book",
        "the_turing_way_reproducible_research",
        "github_readme_docs",
    },
    "career.portfolio": {"github_readme_docs", "the_turing_way_reproducible_research"},
    "career.resume_remote": {"tech_interview_handbook_resume", "tech_interview_handbook"},
}


@dataclass(frozen=True)
class SourceReadinessResult:
    found: dict[str, list[str]]
    missing: dict[str, list[str]]

    @property
    def passed(self) -> bool:
        return not self.missing


def load_resources(path: str | Path = DEFAULT_RESOURCES) -> list[dict[str, Any]]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("resource registry must be a list")
    return [record for record in records if isinstance(record, dict)]


def resource_ids(records: list[dict[str, Any]]) -> set[str]:
    return {str(record.get("id", "")).strip() for record in records if str(record.get("id", "")).strip()}


def check_required_topic_sources(records: list[dict[str, Any]]) -> SourceReadinessResult:
    ids = resource_ids(records)
    found: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    for topic_id, accepted_ids in REQUIRED_TOPIC_SOURCES.items():
        topic_found = sorted(accepted_ids & ids)
        if topic_found:
            found[topic_id] = topic_found
        else:
            missing[topic_id] = sorted(accepted_ids)
    return SourceReadinessResult(found=found, missing=missing)


def format_report(result: SourceReadinessResult) -> str:
    lines = [f"required topics checked: {len(REQUIRED_TOPIC_SOURCES)}"]
    for topic_id in sorted(REQUIRED_TOPIC_SOURCES):
        if topic_id in result.found:
            lines.append(f"PASS {topic_id}: sources found {', '.join(result.found[topic_id])}")
        else:
            lines.append(f"FAIL {topic_id}: missing one of {', '.join(result.missing[topic_id])}")
    lines.append("SOURCE READINESS: PASS" if result.passed else "SOURCE READINESS: FAIL")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check registered source readiness for final gate topics.")
    parser.add_argument("--resources", default=str(DEFAULT_RESOURCES), help="Path to ml_ds_resources.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        records = load_resources(args.resources)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL source readiness: {exc}", file=sys.stderr)
        return 1

    result = check_required_topic_sources(records)
    print(format_report(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
