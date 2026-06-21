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

from core.content_language import LanguageAuditResult, classify_language_text


DEFAULT_VAULT = Path("/Users/mihailkulibaba/Projects/practic_ML/obsidian_vkat")
OUTPUT_JSON = ROOT / "content" / "reports" / "language_report.json"
OUTPUT_MD = ROOT / "content" / "reports" / "language_report.md"
IGNORED_JSON_KEYS = {
    "artifact_paths",
    "dataset_names",
    "datasets",
    "feature_columns",
    "id",
    "path",
    "related_dataset_names",
    "related_practice_ids",
    "related_task_ids",
    "related_theory_paths",
    "skills",
    "source",
    "source_recipe_path",
    "starter_code",
    "target_column",
    "url",
}


def is_hidden_path(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part.startswith(".") for part in relative.parts)


def iter_practice_files(root: Path) -> list[Path]:
    practice_dir = root / "practice"
    if not practice_dir.exists():
        return []
    return sorted(practice_dir.glob("*.md"), key=lambda item: item.name.casefold())


def iter_project_files(root: Path) -> list[Path]:
    project_dir = root / "content" / "projects"
    if not project_dir.exists():
        return []
    return sorted(
        [path for path in project_dir.rglob("*") if path.suffix.lower() in {".json", ".md"}],
        key=lambda item: item.as_posix().casefold(),
    )


def iter_vault_notes(vault: Path | None) -> list[Path]:
    if vault is None or not vault.exists() or not vault.is_dir():
        return []
    return sorted(
        [path for path in vault.rglob("*.md") if not is_hidden_path(path, vault)],
        key=lambda item: item.as_posix().casefold(),
    )


def collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(collect_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for key, item in value.items():
            if str(key).casefold() in IGNORED_JSON_KEYS:
                continue
            strings.extend(collect_strings(item))
        return strings
    return []


def read_content_for_language(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() != ".json":
        return text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    return "\n\n".join(collect_strings(data))


def audit_file(path: Path, root: Path) -> LanguageAuditResult:
    relative = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    return classify_language_text(read_content_for_language(path), relative)


def build_report(results: list[LanguageAuditResult], vault: Path | None) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.classification] = counts.get(result.classification, 0) + 1
    english_heavy = [result for result in results if result.classification == "too_much_english"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "required_language": "Russian learning explanations",
            "allowed_english": [
                "code",
                "identifiers",
                "dataset columns",
                "URLs",
                "official source names",
                "standard ML terms",
            ],
        },
        "metadata": {
            "vault": str(vault) if vault else "",
            "total_files": len(results),
        },
        "summary": {
            "total": len(results),
            "ru_ok": counts.get("ru_ok", 0),
            "mixed_ok": counts.get("mixed_ok", 0),
            "code_or_source_only": counts.get("code_or_source_only", 0),
            "too_much_english": counts.get("too_much_english", 0),
        },
        "files": [asdict(result) for result in results],
        "english_heavy_files": [asdict(result) for result in english_heavy],
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Russian Content Language Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Vault: `{report['metadata'].get('vault', '')}`",
        "",
        "## Policy",
        "",
        "- Learning explanations should be written in Russian.",
        "- English is allowed for code, identifiers, URLs, source names, and standard ML terms.",
        "",
        "## Summary",
        "",
        f"- Total files: {summary['total']}",
        f"- ru_ok: {summary['ru_ok']}",
        f"- mixed_ok: {summary['mixed_ok']}",
        f"- code_or_source_only: {summary['code_or_source_only']}",
        f"- too_much_english: {summary['too_much_english']}",
        "",
        "## English-heavy Files",
        "",
    ]
    if not report["english_heavy_files"]:
        lines.append("No clearly English-heavy learning content found.")
    else:
        for item in report["english_heavy_files"][:100]:
            lines.extend(
                [
                    f"### {item['path']}",
                    f"- Classification: `{item['classification']}`",
                    f"- Cyrillic letters: {item['cyrillic_letters']}",
                    f"- Latin letters: {item['latin_letters']}",
                    f"- Russian ratio: {item['russian_ratio']}",
                    f"- Reason: {item['reason']}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Russian-language learning content coverage.")
    parser.add_argument("--vault", default=os.environ.get("VAULT_PATH", str(DEFAULT_VAULT)))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when English-heavy files are found.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = Path(args.vault).expanduser() if args.vault else None
    if vault is not None and not vault.exists():
        print(f"warning: vault not found, skipping vault notes: {vault}", file=sys.stderr)
        vault = None

    paths = []
    paths.extend(iter_practice_files(ROOT))
    paths.extend(iter_project_files(ROOT))
    paths.extend(iter_vault_notes(vault))
    results = [audit_file(path, ROOT) for path in paths]
    report = build_report(results, vault)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown_report(report), encoding="utf-8")
    summary = report["summary"]
    print(
        "LANGUAGE: "
        f"{summary['ru_ok']} ru_ok, "
        f"{summary['mixed_ok']} mixed_ok, "
        f"{summary['code_or_source_only']} code_or_source_only, "
        f"{summary['too_much_english']} too_much_english"
    )
    print(f"Wrote: {OUTPUT_JSON}")
    print(f"Wrote: {OUTPUT_MD}")
    return 1 if args.strict and summary["too_much_english"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
