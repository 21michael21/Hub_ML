from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK_DIR = PROJECT_ROOT / "content" / "source" / "vkat" / "VKAT-main"
DEFAULT_OUTPUT = PROJECT_ROOT / "content" / "extracted" / "mentor_tasks.json"

TARGET_NOTEBOOK_NAMES = [
    "python_1_start.ipynb",
    "python_2_basics.ipynb",
    "python_2_project.ipynb",
    "python_3_architecture.ipynb",
    "python_4_advanced.ipynb",
    "python_5_OOP.ipynb",
    "python_6_advanced+.ipynb",
    "python_EXTRA_typing.ipynb",
    "analysis_1_stats.ipynb",
    "analysis_2_numpy.ipynb",
    "analysis_3_pandas.ipynb",
]

STUB_PATTERNS = [
    re.compile(r"#\s*TODO\b", re.IGNORECASE),
    re.compile(r"#\s*(?:ваш|ВАШ)\s+код(?:\s+здесь)?", re.IGNORECASE),
    re.compile(r"\.\.\."),
    re.compile(r"\bpass\b"),
    re.compile(r"NotImplementedError", re.IGNORECASE),
]
ASSERT_RE = re.compile(r"^\s*assert\b.*$", re.MULTILINE)
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
TASK_WORD_RE = re.compile(r"\b(?:задание|задача|TODO|упражнение)\b", re.IGNORECASE)


def cell_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return str(source)


def clean_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def first_meaningful_line(text: str) -> str:
    for line in clean_markdown(text).splitlines():
        stripped = line.strip().strip("#").strip()
        if stripped:
            return stripped
    return "Untitled task"


def markdown_title(markdown: str) -> str:
    headings = list(HEADING_RE.finditer(markdown))
    if headings:
        return headings[-1].group(2).strip()
    return first_meaningful_line(markdown)


def find_nearest_markdown(cells: list[dict[str, Any]], code_index: int) -> tuple[int | None, str]:
    for index in range(code_index - 1, -1, -1):
        cell = cells[index]
        if cell.get("cell_type") != "markdown":
            continue
        text = clean_markdown(cell_text(cell))
        if text:
            return index, text
    return None, ""


def stub_hits(code: str) -> list[str]:
    hits: list[str] = []
    for pattern in STUB_PATTERNS:
        if pattern.search(code):
            hits.append(pattern.pattern)
    return hits


def extract_asserts(code: str) -> list[str]:
    return [match.group(0).strip() for match in ASSERT_RE.finditer(code)]


def confidence_for(code: str, prompt: str, asserts: list[str], stubs: list[str]) -> str:
    task_context = bool(TASK_WORD_RE.search(prompt))
    if asserts and stubs and task_context:
        return "high"
    if asserts and stubs:
        return "high"
    if asserts and task_context:
        return "high"
    if stubs and task_context:
        return "medium"
    if stubs:
        return "medium"
    if asserts:
        return "low"
    return "low"


def reasons_for(prompt: str, asserts: list[str], stubs: list[str]) -> list[str]:
    reasons: list[str] = []
    if asserts:
        reasons.append("has_asserts")
    if stubs:
        reasons.append("has_starter_stub")
    if TASK_WORD_RE.search(prompt):
        reasons.append("near_task_markdown")
    if not reasons:
        reasons.append("weak_signal")
    return reasons


def is_candidate(code: str) -> bool:
    return bool(extract_asserts(code) or stub_hits(code))


def extract_tasks_from_notebook(path: Path) -> list[dict[str, Any]]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    tasks: list[dict[str, Any]] = []

    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue

        code = cell_text(cell).strip("\n")
        if not code.strip() or not is_candidate(code):
            continue

        markdown_index, prompt = find_nearest_markdown(cells, index)
        asserts = extract_asserts(code)
        stubs = stub_hits(code)
        confidence = confidence_for(code, prompt, asserts, stubs)
        task_number = len(tasks) + 1
        tasks.append(
            {
                "id": f"{path.stem}__cell_{index}",
                "source_notebook": path.name,
                "source_path": str(path.relative_to(PROJECT_ROOT)),
                "code_cell_index": index,
                "prompt_cell_index": markdown_index,
                "title": markdown_title(prompt) if prompt else f"{path.stem} cell {index}",
                "prompt": prompt,
                "starter_code": code,
                "tests": asserts,
                "has_asserts": bool(asserts),
                "confidence": confidence,
                "signals": reasons_for(prompt, asserts, stubs),
                "task_number_in_notebook": task_number,
            }
        )

    return tasks


def extract_suspicious_markdown_without_candidate(path: Path, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    used_prompt_indexes = {task["prompt_cell_index"] for task in tasks if task["prompt_cell_index"] is not None}
    suspicious: list[dict[str, Any]] = []

    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "markdown" or index in used_prompt_indexes:
            continue
        text = clean_markdown(cell_text(cell))
        if not TASK_WORD_RE.search(text):
            continue

        next_code = None
        for next_index in range(index + 1, min(index + 4, len(cells))):
            if cells[next_index].get("cell_type") == "code":
                next_code = next_index
                break

        suspicious.append(
            {
                "source_notebook": path.name,
                "source_path": str(path.relative_to(PROJECT_ROOT)),
                "markdown_cell_index": index,
                "next_code_cell_index": next_code,
                "title": markdown_title(text),
                "prompt_excerpt": text[:500],
                "reason": "task-like markdown did not map to a candidate code cell",
            }
        )

    return suspicious


def load_notebook_paths(notebook_dir: Path, explicit: list[str] | None = None) -> list[Path]:
    names = explicit or TARGET_NOTEBOOK_NAMES
    paths = [notebook_dir / name for name in names]
    return [path for path in paths if path.exists()]


def build_payload(notebook_paths: list[Path]) -> dict[str, Any]:
    all_tasks: list[dict[str, Any]] = []
    notebooks: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for path in notebook_paths:
        tasks = extract_tasks_from_notebook(path)
        suspicious = extract_suspicious_markdown_without_candidate(path, tasks)
        all_tasks.extend(tasks)
        notebooks.append(
            {
                "name": path.name,
                "path": str(path.relative_to(PROJECT_ROOT)),
                "tasks_extracted": len(tasks),
                "tasks_with_asserts": sum(1 for task in tasks if task["has_asserts"]),
                "confidence": {
                    "high": sum(1 for task in tasks if task["confidence"] == "high"),
                    "medium": sum(1 for task in tasks if task["confidence"] == "medium"),
                    "low": sum(1 for task in tasks if task["confidence"] == "low"),
                },
                "suspicious_markdown_without_candidate": len(suspicious),
            }
        )
        diagnostics.extend(suspicious)

    summary = {
        "notebooks_processed": len(notebook_paths),
        "tasks_extracted": len(all_tasks),
        "tasks_with_asserts": sum(1 for task in all_tasks if task["has_asserts"]),
        "tasks_without_asserts": sum(1 for task in all_tasks if not task["has_asserts"]),
        "confidence": {
            "high": sum(1 for task in all_tasks if task["confidence"] == "high"),
            "medium": sum(1 for task in all_tasks if task["confidence"] == "medium"),
            "low": sum(1 for task in all_tasks if task["confidence"] == "low"),
        },
        "suspicious_markdown_without_candidate": len(diagnostics),
    }
    return {
        "summary": summary,
        "notebooks": notebooks,
        "tasks": all_tasks,
        "diagnostics": {
            "suspicious_markdown_without_candidate": diagnostics,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract mentor notebook tasks into JSON.")
    parser.add_argument("--notebook-dir", type=Path, default=DEFAULT_NOTEBOOK_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--notebook", action="append", dest="notebooks", help="Notebook filename to process.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    notebook_dir = args.notebook_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    notebook_paths = load_notebook_paths(notebook_dir, args.notebooks)

    payload = build_payload(notebook_paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload["summary"]
    print(f"notebooks_processed={summary['notebooks_processed']}")
    print(f"tasks_extracted={summary['tasks_extracted']}")
    print(f"tasks_with_asserts={summary['tasks_with_asserts']}")
    print(f"tasks_without_asserts={summary['tasks_without_asserts']}")
    print(f"confidence={summary['confidence']}")
    print(f"output={output}")


if __name__ == "__main__":
    main()
