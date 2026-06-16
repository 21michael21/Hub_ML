from __future__ import annotations

import ast
import html
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
from core.datasets.registry import find_dataset_record, read_dataset_preview, scan_datasets
from core.notebook.kernel import (
    KernelManager,
    get_notebook_runtime,
    interrupt_notebook_kernel,
    poll_notebook_execution,
    refresh_notebook_kernel_state,
    restart_notebook_kernel,
    start_notebook_cell,
)
from core.notebook.output import render_notebook_output
from core.reports.theory_quality import (
    coverage_by_track,
    coverage_summary,
    load_json_report,
    missing_required_topics,
    report_list,
    theory_summary,
    weakest_notes,
)
from core.tasks.loader import load_mentor_tasks
from core.tasks.models import dataset_snippet_for_task
from core.tasks.runner import (
    build_mentor_task_script,
    classify_task_result,
    run_code_in_notebook_kernel_sync,
    traceback_text,
)

try:
    from streamlit_ace import st_ace
except ImportError:
    st_ace = None

APP_TITLE = "Learning Sandbox — Theory Hub"
NO_SECTION_KEY = "__no_section__"
NO_SECTION_LABEL = "Без раздела"
WIKILINK_RE = re.compile(r"\[\[([^\]\n]+?)\]\]")
MARKDOWN_CODE_RE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
PROGRESS_PATH = Path(__file__).with_name(".learning_progress.json")
PRACTICE_DIR = Path(__file__).with_name("practice")
DATASETS_DIR = Path(__file__).with_name("datasets")
PROJECT_ROOT = Path(__file__).parent
ALGORITHMS_DIR = PROJECT_ROOT / "content" / "source" / "vkat" / "VKAT-main" / "algos_patterns"
INTERVIEW_QUESTIONS_PATH = PROJECT_ROOT / "content" / "interview_questions" / "ml_ds_interview_questions.json"
ARCHITECTURE_GUIDELINES_PATH = PROJECT_ROOT / "content" / "study" / "architecture_guidelines.html"
ARCHITECTURE_GUIDELINES_INDEX_PATH = PROJECT_ROOT / "content" / "study" / "architecture_guidelines_index.json"
MENTOR_TASKS_PATH = PROJECT_ROOT / "content" / "extracted" / "mentor_tasks.json"
THEORY_AUDIT_REPORT_PATH = PROJECT_ROOT / "content" / "reports" / "theory_audit.json"
COVERAGE_REPORT_PATH = PROJECT_ROOT / "content" / "reports" / "coverage_report.json"
STATUS_NOT_STARTED = "not_started"
STATUS_READING = "reading"
STATUS_DONE = "done"
STATUS_REPEAT = "repeat"
PRACTICE_TODO = "todo"
PRACTICE_DOING = "doing"
PRACTICE_DONE = "done"
STATUS_META = {
    STATUS_NOT_STARTED: {"label": "Не начато", "icon": "○", "class": "status-not-started"},
    STATUS_READING: {"label": "Читаю", "icon": "◐", "class": "status-reading"},
    STATUS_DONE: {"label": "Готово", "icon": "●", "class": "status-done"},
    STATUS_REPEAT: {"label": "Повторить", "icon": "↻", "class": "status-repeat"},
}
PRACTICE_META = {
    PRACTICE_TODO: {"label": "Практика не начата", "icon": "□", "class": "status-not-started"},
    PRACTICE_DOING: {"label": "Практика в работе", "icon": "◐", "class": "status-reading"},
    PRACTICE_DONE: {"label": "Практика готова", "icon": "■", "class": "status-done"},
}


st.set_page_config(page_title=APP_TITLE, page_icon="📚", layout="wide")


def inject_styles() -> None:
    st.markdown(
        """
<style>
    :root {
        --ls-muted: rgba(128, 128, 128, 0.82);
        --ls-border: rgba(128, 128, 128, 0.22);
        --ls-soft: rgba(128, 128, 128, 0.10);
        --ls-softer: rgba(128, 128, 128, 0.06);
        --ls-link: rgb(87, 156, 255);
        --ls-link-bg: rgba(87, 156, 255, 0.13);
        --ls-chip-bg: rgba(128, 128, 128, 0.12);
        --ls-code-bg: rgba(128, 128, 128, 0.14);
        --ls-quote-bg: rgba(128, 128, 128, 0.07);
    }

    .main .block-container {
        max-width: 980px;
        padding-top: 2.1rem;
        padding-bottom: 4rem;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        margin-top: 0;
    }

    .sidebar-logo {
        font-size: 1.05rem;
        font-weight: 720;
        letter-spacing: 0;
        padding: 0.15rem 0 0.35rem;
    }

    .note-header {
        max-width: 780px;
        margin: 0 auto 1rem auto;
        padding-bottom: 0.85rem;
        border-bottom: 1px solid var(--ls-border);
    }

    .breadcrumbs {
        color: var(--ls-muted);
        font-size: 0.84rem;
        line-height: 1.45;
        margin-bottom: 0.55rem;
    }

    .frontmatter-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        align-items: center;
    }

    .fm-chip {
        display: inline-flex;
        align-items: center;
        max-width: 100%;
        border: 1px solid var(--ls-border);
        border-radius: 999px;
        padding: 0.15rem 0.55rem;
        background: var(--ls-chip-bg);
        color: var(--text-color);
        font-size: 0.78rem;
        line-height: 1.5;
    }

    div[data-testid="stMarkdownContainer"] {
        max-width: 780px;
        margin-left: auto;
        margin-right: auto;
    }

    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li {
        font-size: 16.5px;
        line-height: 1.68;
    }

    div[data-testid="stMarkdownContainer"] h1 {
        margin-top: 1.2rem;
        margin-bottom: 1rem;
        letter-spacing: 0;
    }

    div[data-testid="stMarkdownContainer"] h2 {
        margin-top: 2.15rem;
        margin-bottom: 0.8rem;
        padding-top: 0.2rem;
        letter-spacing: 0;
    }

    div[data-testid="stMarkdownContainer"] h3 {
        margin-top: 1.7rem;
        margin-bottom: 0.55rem;
        letter-spacing: 0;
    }

    div[data-testid="stMarkdownContainer"] code {
        border-radius: 0.35rem;
        padding: 0.12rem 0.32rem;
        background: var(--ls-code-bg);
        color: var(--text-color);
        font-size: 0.9em;
    }

    div[data-testid="stMarkdownContainer"] pre {
        border: 1px solid var(--ls-border);
        border-radius: 0.7rem;
        background: var(--ls-code-bg);
        overflow-x: auto;
        padding: 1rem;
    }

    div[data-testid="stMarkdownContainer"] pre code {
        padding: 0;
        background: transparent;
        white-space: pre;
    }

    div[data-testid="stMarkdownContainer"] blockquote {
        margin: 1.15rem 0;
        padding: 0.55rem 1rem;
        border-left: 3px solid var(--ls-link);
        background: var(--ls-quote-bg);
        color: var(--ls-muted);
    }

    .obsidian-link {
        display: inline;
        border-radius: 0.35rem;
        padding: 0.06rem 0.32rem;
        background: var(--ls-link-bg);
        color: var(--ls-link);
        font-weight: 600;
        white-space: normal;
    }

    .related-notes {
        max-width: 780px;
        margin: 1.6rem auto 0 auto;
        padding-top: 1rem;
        border-top: 1px solid var(--ls-border);
    }

    .related-notes h3 {
        margin: 0 0 0.8rem 0;
        font-size: 1rem;
        letter-spacing: 0;
    }

    .muted-small {
        color: var(--ls-muted);
        font-size: 0.84rem;
    }

    .learning-panel {
        max-width: 780px;
        margin: 0 auto 1.1rem auto;
        padding: 0.85rem 1rem;
        border: 1px solid var(--ls-border);
        border-radius: 0.85rem;
        background: var(--ls-softer);
    }

    .learning-panel-title {
        margin-bottom: 0.45rem;
        font-weight: 720;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.32rem;
        border: 1px solid var(--ls-border);
        border-radius: 999px;
        padding: 0.16rem 0.6rem;
        font-size: 0.8rem;
        line-height: 1.5;
        background: var(--ls-chip-bg);
    }

    .status-reading {
        color: rgb(250, 176, 84);
        background: rgba(250, 176, 84, 0.12);
    }

    .status-done {
        color: rgb(73, 201, 126);
        background: rgba(73, 201, 126, 0.12);
    }

    .status-repeat {
        color: rgb(250, 106, 106);
        background: rgba(250, 106, 106, 0.12);
    }

    .status-not-started {
        color: var(--ls-muted);
    }

    .roadmap-card {
        padding: 0.85rem 1rem;
        border: 1px solid var(--ls-border);
        border-radius: 0.85rem;
        background: var(--ls-softer);
        margin-bottom: 0.75rem;
    }

    .roadmap-title {
        font-weight: 720;
        margin-bottom: 0.25rem;
    }

    .roadmap-meta {
        color: var(--ls-muted);
        font-size: 0.86rem;
        line-height: 1.5;
    }

    .section-progress-row {
        padding: 0.55rem 0;
        border-bottom: 1px solid var(--ls-border);
    }

    .section-progress-row:last-child {
        border-bottom: 0;
    }

    .link-card {
        border: 1px solid var(--ls-border);
        border-radius: 0.75rem;
        background: var(--ls-softer);
        padding: 0.72rem 0.9rem;
        margin: 0.45rem 0;
    }

    .link-label {
        font-weight: 720;
    }

    .link-path {
        color: var(--ls-muted);
        font-size: 0.82rem;
        line-height: 1.45;
        margin-top: 0.12rem;
    }

    .link-missing {
        opacity: 0.72;
    }

    .health-row {
        border: 1px solid var(--ls-border);
        border-radius: 0.75rem;
        padding: 0.75rem 0.9rem;
        background: var(--ls-softer);
        margin: 0.55rem 0;
    }

    .today-hero {
        max-width: 780px;
        margin: 0 auto 1rem auto;
        padding: 1rem 1.1rem;
        border: 1px solid var(--ls-border);
        border-radius: 0.9rem;
        background: linear-gradient(135deg, rgba(87, 156, 255, 0.12), rgba(73, 201, 126, 0.08));
    }

    .today-title {
        font-size: 1.05rem;
        font-weight: 760;
        margin-bottom: 0.25rem;
    }

    .today-card {
        border: 1px solid var(--ls-border);
        border-radius: 0.85rem;
        padding: 0.85rem 1rem;
        background: var(--ls-softer);
        margin-bottom: 0.75rem;
    }

    .today-card-title {
        font-weight: 760;
        line-height: 1.35;
        margin-bottom: 0.18rem;
    }

    .practice-panel {
        max-width: 780px;
        margin: 1.2rem auto;
        padding: 1rem 1.1rem;
        border: 1px solid var(--ls-border);
        border-radius: 0.9rem;
        background: var(--ls-softer);
    }

    .practice-title {
        font-weight: 760;
        margin-bottom: 0.35rem;
    }

    .practice-output {
        border-left: 3px solid rgb(73, 201, 126);
        padding: 0.45rem 0.8rem;
        margin: 0.75rem 0;
        background: rgba(73, 201, 126, 0.08);
        color: var(--text-color);
    }

    .practice-checklist {
        margin: 0.55rem 0 0 0;
        padding-left: 1.15rem;
    }

    .practice-checklist li {
        margin: 0.28rem 0;
        color: var(--text-color);
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def humanize_section_name(name: str) -> str:
    """Convert vault folder names like data_science into Data Science."""
    if name == NO_SECTION_KEY:
        return NO_SECTION_LABEL

    words = name.replace("_", " ").replace("-", " ").split()
    return " ".join(word.capitalize() for word in words) if words else name


def is_hidden_path(path: Path, vault: Path) -> bool:
    try:
        relative = path.relative_to(vault)
    except ValueError:
        return True

    return any(part.startswith(".") for part in relative.parts)


def get_section_for_file(file_path: Path, vault: Path) -> tuple[str, str]:
    relative = file_path.relative_to(vault)

    if len(relative.parts) == 1:
        return NO_SECTION_KEY, relative.name

    section_key = relative.parts[0]
    display_name = Path(*relative.parts[1:]).as_posix()
    return section_key, display_name


@st.cache_data(show_spinner=False)
def scan_vault(vault_path: str) -> dict[str, list[dict[str, str]]]:
    vault = Path(vault_path).expanduser().resolve()
    sections: dict[str, list[dict[str, str]]] = {}

    for file_path in vault.rglob("*.md"):
        if is_hidden_path(file_path, vault):
            continue

        section_key, display_name = get_section_for_file(file_path, vault)
        relative_path = file_path.relative_to(vault).as_posix()
        sections.setdefault(section_key, []).append(
            {
                "display_name": display_name,
                "path": str(file_path),
                "relative_path": relative_path,
                "section_key": section_key,
                "stem": file_path.stem,
            }
        )

    for notes in sections.values():
        notes.sort(key=lambda note: note["display_name"].casefold())

    return dict(
        sorted(
            sections.items(),
            key=lambda item: (item[0] != NO_SECTION_KEY, humanize_section_name(item[0]).casefold()),
        )
    )


def read_note(path: str) -> tuple[str, str | None]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return "", str(exc)


def load_progress() -> dict[str, Any]:
    if not PROGRESS_PATH.exists():
        return {
            "notes": {},
            "practice_status": {},
            "portfolio_outputs": {},
            "algos_status": {},
            "mentor_tasks_status": {},
        }

    try:
        data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "notes": {},
            "practice_status": {},
            "portfolio_outputs": {},
            "algos_status": {},
            "mentor_tasks_status": {},
        }

    if not isinstance(data, dict):
        return {
            "notes": {},
            "practice_status": {},
            "portfolio_outputs": {},
            "algos_status": {},
            "mentor_tasks_status": {},
        }
    if not isinstance(data.get("notes"), dict):
        data["notes"] = {}
    data.pop("practice", None)
    if not isinstance(data.get("practice_status"), dict):
        data["practice_status"] = {}
    if not isinstance(data.get("portfolio_outputs"), dict):
        data["portfolio_outputs"] = {}
    if not isinstance(data.get("algos_status"), dict):
        data["algos_status"] = {}
    if not isinstance(data.get("mentor_tasks_status"), dict):
        data["mentor_tasks_status"] = {}
    return data


def save_progress(progress: dict[str, Any]) -> None:
    try:
        PROGRESS_PATH.write_text(
            json.dumps(progress, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        st.warning(f"Не удалось сохранить прогресс: {exc}")


def ensure_progress_state() -> dict[str, Any]:
    if "learning_progress" not in st.session_state:
        st.session_state["learning_progress"] = load_progress()
    return st.session_state["learning_progress"]


def note_progress_key(note: dict[str, str]) -> str:
    return note["relative_path"]


def get_note_status(note: dict[str, str]) -> str:
    progress = ensure_progress_state()
    record = progress.get("notes", {}).get(note_progress_key(note), {})
    status = record.get("status", STATUS_NOT_STARTED)
    return status if status in STATUS_META else STATUS_NOT_STARTED


def status_badge(status: str) -> str:
    meta = STATUS_META.get(status, STATUS_META[STATUS_NOT_STARTED])
    return (
        f'<span class="status-pill {meta["class"]}">'
        f'{html.escape(meta["icon"])} {html.escape(meta["label"])}</span>'
    )


def practice_badge(status: str) -> str:
    meta = PRACTICE_META.get(status, PRACTICE_META[PRACTICE_TODO])
    return (
        f'<span class="status-pill {meta["class"]}">'
        f'{html.escape(meta["icon"])} {html.escape(meta["label"])}</span>'
    )


def set_note_status_by_key(note_key: str, status: str) -> None:
    if status not in STATUS_META:
        return

    progress = ensure_progress_state()
    progress.setdefault("notes", {})[note_key] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_progress(progress)


def get_practice_record(note: dict[str, str]) -> dict[str, Any]:
    progress = ensure_progress_state()
    record = progress.setdefault("practice", {}).get(note_progress_key(note), {})
    return record if isinstance(record, dict) else {}


def get_practice_status(note: dict[str, str]) -> str:
    status = get_practice_record(note).get("status", PRACTICE_TODO)
    return status if status in PRACTICE_META else PRACTICE_TODO


def set_practice_status_by_key(note_key: str, status: str) -> None:
    if status not in PRACTICE_META:
        return

    progress = ensure_progress_state()
    record = progress.setdefault("practice", {}).setdefault(note_key, {})
    record["status"] = status
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_progress(progress)


def save_practice_note_by_key(note_key: str, widget_key: str) -> None:
    progress = ensure_progress_state()
    record = progress.setdefault("practice", {}).setdefault(note_key, {})
    record["notes"] = st.session_state.get(widget_key, "")
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_progress(progress)


def start_practice_by_key(note_key: str) -> None:
    set_practice_status_by_key(note_key, PRACTICE_DOING)
    progress = ensure_progress_state()
    current_status = progress.get("notes", {}).get(note_key, {}).get("status", STATUS_NOT_STARTED)
    if current_status == STATUS_NOT_STARTED:
        set_note_status_by_key(note_key, STATUS_READING)


def finish_practice_by_key(note_key: str) -> None:
    set_practice_status_by_key(note_key, PRACTICE_DONE)
    set_note_status_by_key(note_key, STATUS_DONE)


def section_progress(notes: list[dict[str, str]]) -> dict[str, int]:
    counts = {status: 0 for status in STATUS_META}
    for note in notes:
        counts[get_note_status(note)] += 1
    counts["total"] = len(notes)
    return counts


def all_notes(sections: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    for section_notes in sections.values():
        notes.extend(section_notes)
    return notes


def completion_ratio(notes: list[dict[str, str]]) -> float:
    if not notes:
        return 0.0
    done = sum(1 for note in notes if get_note_status(note) == STATUS_DONE)
    return done / len(notes)


def find_next_note(sections: dict[str, list[dict[str, str]]]) -> dict[str, str] | None:
    preferred_sections = [
        "00_Atlas",
        "01_Python",
        "02_Data_Analysis",
        "03_ML",
        "04_NLP",
        "05_IT_Resources",
    ]
    ordered_keys = [key for key in preferred_sections if key in sections]
    ordered_keys.extend(key for key in sections if key not in ordered_keys)

    for key in ordered_keys:
        for note in sections[key]:
            if get_note_status(note) != STATUS_DONE:
                return note
    return None


def ordered_learning_notes(sections: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    preferred_sections = [
        "00_Atlas",
        "01_Python",
        "02_Data_Analysis",
        "03_ML",
        "04_NLP",
        "05_IT_Resources",
    ]
    ordered_keys = [key for key in preferred_sections if key in sections]
    ordered_keys.extend(key for key in sections if key not in ordered_keys)

    notes: list[dict[str, str]] = []
    for key in ordered_keys:
        notes.extend(sections[key])
    return notes


def today_notes(sections: dict[str, list[dict[str, str]]], limit: int = 3) -> list[dict[str, str]]:
    candidates = [note for note in ordered_learning_notes(sections) if get_note_status(note) != STATUS_DONE]
    priority = {
        STATUS_REPEAT: 0,
        STATUS_READING: 1,
        STATUS_NOT_STARTED: 2,
        STATUS_DONE: 3,
    }
    candidates.sort(
        key=lambda note: (
            priority.get(get_note_status(note), 9),
            note["section_key"].casefold(),
            note["display_name"].casefold(),
        )
    )
    return candidates[:limit]


def safe_widget_key(prefix: str, value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    return f"{prefix}_{cleaned[:90]}"


def note_title(note: dict[str, str], frontmatter: dict[str, Any] | None = None) -> str:
    title = (frontmatter or {}).get("title")
    if title:
        return str(title)
    return Path(note["display_name"]).stem.replace("_", " ")


def practice_template(note: dict[str, str], frontmatter: dict[str, Any] | None = None) -> dict[str, Any]:
    title = note_title(note, frontmatter)
    context = f"{note['section_key']} {note['display_name']}".casefold()

    if "nlp" in context or "prompt" in context or "llm" in context:
        return {
            "title": f"NLP/AI практика: {title}",
            "objective": "Преврати идею заметки в маленький эксперимент с текстом, промптом или оценкой ответа.",
            "output": "Мини-отчет: задача, входные данные/промпт, 3 результата, вывод что улучшить.",
            "checklist": [
                "Сформулировал рабочую задачу как для реального проекта.",
                "Подготовил 3 тестовых примера или промпта.",
                "Записал наблюдения: что сработало, что ломается, какой следующий эксперимент.",
            ],
        }

    if "ml" in context or "model" in context or "classification" in context or "regression" in context:
        return {
            "title": f"ML практика: {title}",
            "objective": "Собери baseline-мышление: данные, метрика, простая модель, ошибка, следующий шаг.",
            "output": "Один markdown-отчет или notebook-план: problem → metric → baseline → error analysis.",
            "checklist": [
                "Определил target и метрику качества.",
                "Описал простой baseline без переусложнения.",
                "Нашел 2 возможные причины ошибок и 1 идею улучшения.",
            ],
        }

    if "data" in context or "pandas" in context or "analytics" in context or "dataset" in context:
        return {
            "title": f"Data практика: {title}",
            "objective": "Сделай из темы заметки маленький аналитический сценарий, как на рабочей задаче.",
            "output": "EDA-заметка: 5 проверок данных, 3 инсайта, 1 визуализация или таблица вывода.",
            "checklist": [
                "Проверил форму данных, пропуски, типы и странные значения.",
                "Сформулировал 3 бизнесовых или продуктовых вывода.",
                "Описал, какое решение можно принять на основе анализа.",
            ],
        }

    if "python" in context or "code" in context or "algorithm" in context:
        return {
            "title": f"Python практика: {title}",
            "objective": "Закрепи тему через небольшой рабочий фрагмент кода и самопроверку.",
            "output": "Файл или gist-план: функция/класс, 3 примера использования, 2 edge case.",
            "checklist": [
                "Написал минимальную реализацию по теме.",
                "Проверил 3 обычных сценария и 2 краевых случая.",
                "Сформулировал, где это пригодится в ML/NLP работе.",
            ],
        }

    if "career" in context or "interview" in context or "resume" in context or "it" in context:
        return {
            "title": f"Career/IT практика: {title}",
            "objective": "Переведи заметку в карьерный артефакт: ответ на собеседование, bullet для резюме или рабочий чеклист.",
            "output": "Готовый текст: STAR-ответ, resume bullet или чеклист из 5 пунктов.",
            "checklist": [
                "Сформулировал ситуацию и свою роль конкретно.",
                "Добавил измеримый результат или техническую деталь.",
                "Сделал текст коротким и пригодным для LinkedIn/CV/интервью.",
            ],
        }

    return {
        "title": f"Практика: {title}",
        "objective": "Сделай из заметки один маленький рабочий артефакт, который можно показать или использовать дальше.",
        "output": "Короткая заметка: что понял, где применил, какой следующий эксперимент.",
        "checklist": [
            "Выделил главную идею заметки.",
            "Применил ее на маленьком примере.",
            "Записал следующий шаг, который приблизит к ML/NLP работе.",
        ],
    }


def parse_scalar(value: str) -> Any:
    value = value.strip()

    if not value:
        return ""

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",")]

    lowered = value.casefold()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None

    return value.strip("\"'")


def parse_simple_frontmatter(block: str) -> dict[str, Any]:
    frontmatter: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in block.splitlines():
        line = raw_line.rstrip()

        if not line.strip() or line.lstrip().startswith("#"):
            continue

        stripped = line.strip()
        if stripped.startswith("- ") and current_list_key:
            frontmatter.setdefault(current_list_key, []).append(parse_scalar(stripped[2:]))
            continue

        current_list_key = None
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if value:
            frontmatter[key] = parse_scalar(value)
        else:
            frontmatter[key] = []
            current_list_key = key

    return frontmatter


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        return {}, text

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            block = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :]).lstrip("\n")
            return parse_simple_frontmatter(block), body

    return {}, text


def render_frontmatter_chips(frontmatter: dict[str, Any]) -> str:
    if not frontmatter:
        return ""

    chips: list[str] = []
    for key, value in frontmatter.items():
        if isinstance(value, list):
            rendered_values = [str(item) for item in value if str(item)]
            if key == "tags":
                chips.extend(
                    f'<span class="fm-chip">#{html.escape(item)}</span>' for item in rendered_values
                )
                continue
            rendered = ", ".join(rendered_values)
        elif value is None:
            rendered = "null"
        else:
            rendered = str(value)

        if rendered:
            chips.append(
                f'<span class="fm-chip">{html.escape(key)}: {html.escape(rendered)}</span>'
            )

    if not chips:
        return ""

    return '<div class="frontmatter-row">' + "".join(chips) + "</div>"


def normalize_link_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    while value.endswith(".md"):
        value = value[:-3]
    return value.strip("/")


def split_wikilink(raw: str) -> dict[str, str | None]:
    target_part, explicit_label = (raw.split("|", 1) + [None])[:2] if "|" in raw else (raw, None)
    target_part = target_part.strip()
    explicit_label = explicit_label.strip() if explicit_label else None

    link_type: str | None = None
    subtarget: str | None = None
    file_target = target_part

    if "#" in target_part:
        file_target, subtarget = target_part.split("#", 1)
        link_type = "heading"
    elif "^" in target_part:
        file_target, subtarget = target_part.split("^", 1)
        link_type = "block"

    file_target = normalize_link_path(file_target)
    subtarget = subtarget.strip() if subtarget else None

    if explicit_label:
        label = explicit_label
    elif link_type == "heading" and subtarget:
        base = Path(file_target).name if file_target else "Текущая заметка"
        label = f"{base} › {subtarget}"
    else:
        label = target_part.strip()

    return {
        "target": target_part.strip(),
        "file_target": file_target,
        "subtarget": subtarget,
        "link_type": link_type,
        "label": label,
    }


def extract_wikilinks(markdown_text: str) -> list[dict[str, str | None]]:
    markdown_text = strip_markdown_code_for_links(markdown_text)
    links: list[dict[str, str | None]] = []
    for match in WIKILINK_RE.finditer(markdown_text):
        parsed = split_wikilink(match.group(1))
        if parsed["target"]:
            parsed["raw"] = match.group(0)
            links.append(parsed)
    return links


def strip_markdown_code_for_links(markdown_text: str) -> str:
    return MARKDOWN_CODE_RE.sub("", markdown_text)


def with_md_suffix(path: Path) -> Path:
    if path.suffix.casefold() == ".md":
        return path
    return Path(f"{path}.md")


def index_path_key(path: Path) -> str:
    return normalize_link_path(path.as_posix()).casefold()


def build_note_index(sections: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    note_by_path: dict[str, dict[str, str]] = {}
    stem_index: dict[str, list[dict[str, str]]] = {}
    rel_index: dict[str, dict[str, str]] = {}

    for notes in sections.values():
        for note in notes:
            note_by_path[note["path"]] = note
            stem_index.setdefault(note["stem"].casefold(), []).append(note)
            relative = Path(note["relative_path"])
            rel_index[index_path_key(relative)] = note
            rel_index[relative.as_posix().casefold()] = note

    for matches in stem_index.values():
        matches.sort(key=lambda note: note["relative_path"].casefold())

    return {
        "note_by_path": note_by_path,
        "stem_index": stem_index,
        "rel_index": rel_index,
        "all_notes": all_notes(sections),
    }


def common_prefix_len(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    count = 0
    for left_part, right_part in zip(left, right, strict=False):
        if left_part.casefold() != right_part.casefold():
            break
        count += 1
    return count


def choose_nearest_note(
    matches: list[dict[str, str]],
    current_note: dict[str, str],
) -> dict[str, str] | None:
    if not matches:
        return None

    current_parts = Path(current_note["relative_path"]).parent.parts

    def score(note: dict[str, str]) -> tuple[int, int, str]:
        note_parts = Path(note["relative_path"]).parent.parts
        shared = common_prefix_len(current_parts, note_parts)
        distance = (len(current_parts) - shared) + (len(note_parts) - shared)
        return (-shared, distance, note["relative_path"].casefold())

    return sorted(matches, key=score)[0]


def resolve_wikilink_detail(
    link: dict[str, str | None],
    current_note: dict[str, str],
    vault: Path,
    note_index: dict[str, Any],
) -> dict[str, Any]:
    file_target = str(link.get("file_target") or "")
    note_by_path: dict[str, dict[str, str]] = note_index["note_by_path"]
    rel_index: dict[str, dict[str, str]] = note_index["rel_index"]
    stem_index: dict[str, list[dict[str, str]]] = note_index["stem_index"]

    if not file_target:
        return {
            "status": "resolved",
            "note": current_note,
            "matches": [current_note],
            "reason": "Текущая заметка",
        }

    current_relative_dir = Path(current_note["relative_path"]).parent
    relative_candidates = [
        index_path_key(current_relative_dir / file_target),
        index_path_key(Path(file_target)),
    ]

    for candidate_key in relative_candidates:
        if candidate_key in rel_index:
            note = rel_index[candidate_key]
            return {
                "status": "resolved",
                "note": note,
                "matches": [note],
                "reason": "resolved",
            }

    for candidate in (with_md_suffix(Path(current_note["path"]).parent / file_target), with_md_suffix(vault / file_target)):
        try:
            resolved = str(candidate.expanduser().resolve())
        except OSError:
            continue
        if resolved in note_by_path:
            note = note_by_path[resolved]
            return {
                "status": "resolved",
                "note": note,
                "matches": [note],
                "reason": "resolved",
            }

    stem = Path(file_target).stem.casefold()
    matches = stem_index.get(stem, [])
    if len(matches) > 1:
        chosen = choose_nearest_note(matches, current_note)
        return {
            "status": "ambiguous",
            "note": chosen,
            "matches": matches,
            "reason": f"Неоднозначная ссылка: найдено {len(matches)} файлов",
        }
    if len(matches) == 1:
        return {
            "status": "resolved",
            "note": matches[0],
            "matches": matches,
            "reason": "resolved",
        }

    return {
        "status": "missing",
        "note": None,
        "matches": [],
        "reason": "Файл не найден",
    }


def label_for_link(link: dict[str, str | None]) -> str:
    return str(link.get("label") or link.get("target") or "")


def dedupe_link_key(link: dict[str, Any]) -> str:
    resolved = link.get("resolved_note")
    if resolved:
        suffix = link.get("subtarget") or ""
        return f'{resolved["path"]}#{suffix}'.casefold()
    return str(link.get("target") or "").casefold()


def render_markdown_with_wikilinks(markdown_text: str) -> str:
    markdown_text = markdown_text or "_Пустая заметка._"

    def replace_match(match: re.Match[str]) -> str:
        parsed = split_wikilink(match.group(1))
        rendered_label = html.escape(label_for_link(parsed))
        return f'<span class="obsidian-link">🔗 {rendered_label}</span>'

    rendered_parts: list[str] = []
    last_end = 0
    for code_match in MARKDOWN_CODE_RE.finditer(markdown_text):
        before = markdown_text[last_end : code_match.start()]
        escaped_before = html.escape(before, quote=False)
        rendered_parts.append(WIKILINK_RE.sub(replace_match, escaped_before))
        rendered_parts.append(html.escape(code_match.group(0), quote=False))
        last_end = code_match.end()

    tail = markdown_text[last_end:]
    escaped_tail = html.escape(tail, quote=False)
    rendered_parts.append(WIKILINK_RE.sub(replace_match, escaped_tail))
    return "".join(rendered_parts)


def collect_outgoing_links(
    markdown_text: str,
    current_note: dict[str, str],
    vault: Path,
    note_index: dict[str, Any],
) -> list[dict[str, Any]]:
    outgoing: list[dict[str, Any]] = []
    seen: set[str] = set()

    for link in extract_wikilinks(markdown_text):
        resolution = resolve_wikilink_detail(link, current_note, vault, note_index)
        resolved_note = resolution["note"]
        record = {
            **link,
            "source_note": current_note,
            "resolved_note": resolved_note,
            "status": resolution["status"],
            "reason": resolution["reason"],
            "matches": resolution["matches"],
        }
        key = dedupe_link_key(record)
        if key in seen:
            continue
        seen.add(key)
        outgoing.append(record)

    return outgoing


@st.cache_data(show_spinner=False)
def scan_link_graph(vault_path: str) -> dict[str, Any]:
    vault = Path(vault_path).expanduser().resolve()
    sections = scan_vault(str(vault))
    note_index = build_note_index(sections)
    outgoing_by_path: dict[str, list[dict[str, Any]]] = {}
    backlinks_by_path: dict[str, list[dict[str, Any]]] = {}
    broken: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    total = 0
    resolved = 0

    for note in note_index["all_notes"]:
        text, error = read_note(note["path"])
        if error:
            outgoing_by_path[note["path"]] = []
            continue
        _, body = split_frontmatter(text)
        records = collect_outgoing_links(body, note, vault, note_index)
        outgoing_by_path[note["path"]] = records

        for record in records:
            total += 1
            status = record["status"]
            if status in {"resolved", "ambiguous"} and record["resolved_note"]:
                resolved += 1
                backlinks_by_path.setdefault(record["resolved_note"]["path"], []).append(record)
            if status == "missing":
                broken.append(record)
            elif status == "ambiguous":
                ambiguous.append(record)

    return {
        "outgoing_by_path": outgoing_by_path,
        "backlinks_by_path": backlinks_by_path,
        "broken": broken,
        "ambiguous": ambiguous,
        "summary": {
            "total": total,
            "resolved": resolved,
            "broken": len(broken),
            "ambiguous": len(ambiguous),
        },
    }


def listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    value_text = str(value).strip()
    return [value_text] if value_text else []


def practice_card_id(path: Path, practice_dir: Path = PRACTICE_DIR) -> str:
    try:
        return path.relative_to(practice_dir).as_posix()
    except ValueError:
        return path.name


def normalize_related_note(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]"):
        text = text[2:-2]
    parsed = split_wikilink(text)
    return str(parsed.get("file_target") or parsed.get("target") or "").strip()


def scan_practice_cards() -> tuple[list[dict[str, Any]], list[str]]:
    if not PRACTICE_DIR.exists() or not PRACTICE_DIR.is_dir():
        return [], []

    cards: list[dict[str, Any]] = []
    warnings: list[str] = []
    required_fields = {"title", "section", "difficulty", "est_time"}

    for card_path in sorted(PRACTICE_DIR.rglob("*.md"), key=lambda path: path.as_posix().casefold()):
        if any(part.startswith(".") for part in card_path.relative_to(PRACTICE_DIR).parts):
            continue

        text, error = read_note(str(card_path))
        if error:
            warnings.append(f"{card_path.name}: не удалось прочитать файл ({error})")
            continue

        frontmatter, body = split_frontmatter(text)
        missing = sorted(field for field in required_fields if not str(frontmatter.get(field, "")).strip())
        difficulty = str(frontmatter.get("difficulty", "")).strip().casefold()
        if missing or difficulty not in {"easy", "medium", "hard"}:
            problem = ", ".join(missing) if missing else f"difficulty={difficulty!r}"
            warnings.append(f"{card_path.name}: битый или неполный frontmatter ({problem})")
            continue

        card_id = practice_card_id(card_path)
        cards.append(
            {
                "id": card_id,
                "path": str(card_path),
                "title": str(frontmatter["title"]).strip(),
                "section": str(frontmatter["section"]).strip(),
                "difficulty": difficulty,
                "est_time": str(frontmatter["est_time"]).strip(),
                "related_note": normalize_related_note(frontmatter.get("related_note", "")),
                "dataset": str(frontmatter.get("dataset", "")).strip(),
                "links": listify(frontmatter.get("links")),
                "frontmatter": frontmatter,
                "body": body.strip() or "_Карточка пока пустая._",
            }
        )

    return cards, warnings


def get_card_status(card: dict[str, Any]) -> str:
    progress = ensure_progress_state()
    record = progress.setdefault("practice_status", {}).get(card["id"], {})
    status = record.get("status", PRACTICE_TODO) if isinstance(record, dict) else PRACTICE_TODO
    return status if status in PRACTICE_META else PRACTICE_TODO


def set_card_status(card_id: str, status: str) -> None:
    if status not in PRACTICE_META:
        return

    progress = ensure_progress_state()
    progress.setdefault("practice_status", {})[card_id] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_progress(progress)


def resolve_related_note(
    related_note: str,
    note_index: dict[str, Any],
) -> dict[str, str] | None:
    target = normalize_related_note(related_note)
    if not target:
        return None

    rel_index: dict[str, dict[str, str]] = note_index["rel_index"]
    stem_index: dict[str, list[dict[str, str]]] = note_index["stem_index"]

    rel_match = rel_index.get(index_path_key(Path(target)))
    if rel_match:
        return rel_match

    matches = stem_index.get(Path(target).stem.casefold(), [])
    return matches[0] if matches else None


def cards_for_note(
    cards: list[dict[str, Any]],
    note: dict[str, str],
    note_index: dict[str, Any],
) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    for card in cards:
        resolved = resolve_related_note(str(card.get("related_note") or ""), note_index)
        if resolved and resolved["path"] == note["path"]:
            related.append(card)
    return related


def practice_progress(cards: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in PRACTICE_META}
    for card in cards:
        counts[get_card_status(card)] += 1
    counts["total"] = len(cards)
    return counts


def get_output_record(card_id: str) -> dict[str, Any]:
    progress = ensure_progress_state()
    record = progress.setdefault("portfolio_outputs", {}).get(card_id, {})
    return record if isinstance(record, dict) else {}


def output_has_content(record: dict[str, Any]) -> bool:
    return any(str(record.get(field, "")).strip() for field in ("summary", "artifact", "reflection"))


def card_has_output(card: dict[str, Any]) -> bool:
    return output_has_content(get_output_record(card["id"]))


def save_output_record(
    card_id: str,
    summary: str,
    artifact: str,
    reflection: str,
) -> None:
    progress = ensure_progress_state()
    progress.setdefault("portfolio_outputs", {})[card_id] = {
        "summary": summary.strip(),
        "artifact": artifact.strip(),
        "reflection": reflection.strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_progress(progress)


def clear_output_record(card_id: str) -> None:
    progress = ensure_progress_state()
    progress.setdefault("portfolio_outputs", {}).pop(card_id, None)
    save_progress(progress)


def portfolio_progress(cards: list[dict[str, Any]]) -> dict[str, int]:
    total = len(cards)
    with_outputs = sum(1 for card in cards if card_has_output(card))
    return {"total": total, "with_outputs": with_outputs, "missing": total - with_outputs}


def humanize_algorithm_name(path: Path) -> str:
    stem = re.sub(r"^\d+[_-]*", "", path.stem)
    words = [word for word in re.split(r"[_\-\s]+", stem) if word]
    if not words:
        return path.stem
    replacements = {"o": "O", "oop": "OOP"}
    return " ".join(replacements.get(word.casefold(), word.capitalize()) for word in words)


def algorithm_sort_key(path: Path) -> tuple[int, str]:
    match = re.match(r"^(\d+)", path.name)
    number = int(match.group(1)) if match else 10_000
    return number, path.name.casefold()


def extract_module_docstring(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return ""
    return ast.get_docstring(tree, clean=True) or ""


@st.cache_data(show_spinner=False)
def scan_algorithm_lessons() -> list[dict[str, Any]]:
    if not ALGORITHMS_DIR.exists() or not ALGORITHMS_DIR.is_dir():
        return []

    lessons: list[dict[str, Any]] = []
    for lesson_path in sorted(ALGORITHMS_DIR.glob("*.py"), key=algorithm_sort_key):
        if lesson_path.name.startswith(".") or lesson_path.name == "__init__.py":
            continue

        text, error = read_note(str(lesson_path))
        lessons.append(
            {
                "id": lesson_path.name,
                "path": str(lesson_path),
                "title": humanize_algorithm_name(lesson_path),
                "docstring": extract_module_docstring(lesson_path),
                "code": text,
                "error": error,
            }
        )

    return lessons


def get_algorithm_status(lesson_id: str) -> str:
    progress = ensure_progress_state()
    record = progress.setdefault("algos_status", {}).get(lesson_id, {})
    status = record.get("status", STATUS_NOT_STARTED) if isinstance(record, dict) else STATUS_NOT_STARTED
    return STATUS_DONE if status == STATUS_DONE else STATUS_NOT_STARTED


def set_algorithm_status(lesson_id: str, status: str, result: dict[str, Any] | None = None) -> None:
    progress = ensure_progress_state()
    record: dict[str, Any] = {
        "status": STATUS_DONE if status == STATUS_DONE else STATUS_NOT_STARTED,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if result:
        record["last_exit_code"] = result.get("exit_code")
        record["last_elapsed"] = result.get("elapsed")
    progress.setdefault("algos_status", {})[lesson_id] = record
    save_progress(progress)


def algorithm_progress(lessons: list[dict[str, Any]]) -> dict[str, int]:
    total = len(lessons)
    done = sum(1 for lesson in lessons if get_algorithm_status(lesson["id"]) == STATUS_DONE)
    return {"total": total, "done": done, "todo": total - done}


def run_algorithm_tests(lesson_path: str, timeout_seconds: int = 30) -> dict[str, Any]:
    started = time.perf_counter()
    path = Path(lesson_path).expanduser().resolve()
    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "exit_code": completed.returncode,
            "elapsed": time.perf_counter() - started,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "timed_out": True,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "exit_code": None,
            "elapsed": time.perf_counter() - started,
        }
    except OSError as exc:
        return {
            "timed_out": False,
            "stdout": "",
            "stderr": str(exc),
            "exit_code": None,
            "elapsed": time.perf_counter() - started,
        }


def get_mentor_task_status(task_id: str) -> str:
    progress = ensure_progress_state()
    record = progress.setdefault("mentor_tasks_status", {}).get(task_id, {})
    status = record.get("status", STATUS_NOT_STARTED) if isinstance(record, dict) else STATUS_NOT_STARTED
    return STATUS_DONE if status == STATUS_DONE else STATUS_NOT_STARTED


def set_mentor_task_status(task_id: str, status: str, result: dict[str, Any] | None = None) -> None:
    progress = ensure_progress_state()
    record: dict[str, Any] = {
        "status": STATUS_DONE if status == STATUS_DONE else STATUS_NOT_STARTED,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if result:
        record["last_elapsed"] = result.get("elapsed")
        record["last_error"] = result.get("error")
    progress.setdefault("mentor_tasks_status", {})[task_id] = record
    save_progress(progress)


def mentor_tasks_progress(tasks: list[dict[str, Any]]) -> dict[str, int]:
    reviewable = [task for task in tasks if task["confidence"] != "low"]
    done = sum(1 for task in reviewable if get_mentor_task_status(task["id"]) == STATUS_DONE)
    return {"total": len(reviewable), "done": done, "todo": len(reviewable) - done}


@st.cache_data(show_spinner=False)
def load_interview_questions() -> dict[str, Any]:
    if not INTERVIEW_QUESTIONS_PATH.exists():
        return {"companies": [], "total_companies": 0}

    try:
        data = json.loads(INTERVIEW_QUESTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"companies": [], "total_companies": 0}

    companies = data.get("companies", [])
    if not isinstance(companies, list):
        companies = []

    normalized: list[dict[str, Any]] = []
    for entry in companies:
        if not isinstance(entry, dict):
            continue
        company = str(entry.get("company") or "").strip()
        if not company:
            continue
        questions = [str(item).strip() for item in entry.get("questions", []) if str(item).strip()]
        tasks = [str(item).strip() for item in entry.get("tasks", []) if str(item).strip()]
        notes = [str(item).strip() for item in entry.get("notes", []) if str(item).strip()]
        normalized.append(
            {
                "company": company,
                "questions": questions,
                "tasks": tasks,
                "notes": notes,
                "relevance": str(entry.get("relevance") or "").strip(),
            }
        )

    return {
        "companies": normalized,
        "total_companies": len(normalized),
        "total_questions": sum(len(item["questions"]) for item in normalized),
        "total_tasks": sum(len(item["tasks"]) for item in normalized),
    }


def strip_html_tags(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags).replace("\xa0", " ")).strip()


@st.cache_data(show_spinner=False)
def load_architecture_guidelines() -> dict[str, Any]:
    if not ARCHITECTURE_GUIDELINES_PATH.exists():
        return {"title": "Архитектурные рекомендации", "html": "", "sections": []}

    try:
        raw_html = ARCHITECTURE_GUIDELINES_PATH.read_text(encoding="utf-8")
    except OSError:
        return {"title": "Архитектурные рекомендации", "html": "", "sections": []}

    try:
        index_data = json.loads(ARCHITECTURE_GUIDELINES_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        index_data = {}

    title = str(index_data.get("title") or "Архитектурные рекомендации")
    matches = list(re.finditer(r'<h4\s+id="([^"]+)"[^>]*>(.*?)</h4>', raw_html, flags=re.I | re.S))
    sections: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_html)
        section_html = raw_html[start:end].strip()
        section_title = strip_html_tags(match.group(2))
        if section_title:
            sections.append({"id": match.group(1), "title": section_title, "html": section_html})

    document_html = re.sub(r"</?body[^>]*>", "", raw_html, flags=re.I).strip()
    return {"title": title, "html": document_html, "sections": sections}


def open_dataset_tab(dataset_name: str) -> None:
    st.session_state["selected_dataset"] = dataset_name
    st.session_state["active_tab"] = "📊 Datasets"


def open_dataset_from_card(dataset_name: str, card_id: str) -> None:
    st.session_state["dataset_return_card"] = card_id
    open_dataset_tab(dataset_name)


def notebook_dataset_starter_code(dataset_name: str) -> str:
    safe_dataset = Path(str(dataset_name)).name
    dataset_path = f"datasets/{safe_dataset}"
    return f'''import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv({dataset_path!r})
display(df.head())

print("shape:", df.shape)
print("columns:", list(df.columns))

if {{"category", "revenue"}}.issubset(df.columns):
    df.groupby("category")["revenue"].sum().sort_values().plot(
        kind="barh",
        title="Revenue by category",
        figsize=(7, 4),
    )
    plt.tight_layout()
    plt.show()
'''


def open_dataset_in_notebook(dataset_name: str) -> None:
    init_notebook_state()
    counter = int(st.session_state.get("notebook_cell_counter", 0)) + 1
    st.session_state["notebook_cell_counter"] = counter
    cell_id = f"cell_{counter}"
    st.session_state["notebook_cells"].append({"id": cell_id})
    st.session_state[f"notebook_code_{cell_id}"] = notebook_dataset_starter_code(dataset_name)
    st.session_state["notebook_plain_editor"] = True
    st.session_state["active_tab"] = "📓 Notebook"


def default_scratch_code(datasets: list[dict[str, Any]]) -> str:
    dataset_name = "df_orders.csv"
    if not find_dataset_record(dataset_name, datasets) and datasets:
        dataset_name = datasets[0]["name"]

    return f'''from pathlib import Path

import pandas as pd

dataset_path = Path("datasets") / "{dataset_name}"
print(f"Reading {{dataset_path}}")

if not dataset_path.exists():
    print("Dataset file not found. Add CSV files to the datasets/ folder.")
else:
    df = pd.read_csv(dataset_path)
    print("shape:", df.shape)
    print(df.head())
'''


def run_scratch_code(code: str, timeout_seconds: int) -> dict[str, Any]:
    started = time.perf_counter()
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".py",
            encoding="utf-8",
            dir=PROJECT_ROOT,
            delete=False,
        ) as handle:
            handle.write(code)
            temp_path = Path(handle.name)

        completed = subprocess.run(
            [sys.executable, str(temp_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "exit_code": completed.returncode,
            "elapsed": time.perf_counter() - started,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "timed_out": True,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "exit_code": None,
            "elapsed": time.perf_counter() - started,
        }
    finally:
        if temp_path:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def init_notebook_state() -> None:
    if "notebook_cells" not in st.session_state:
        st.session_state["notebook_cells"] = [
            {"id": "cell_1"},
            {"id": "cell_2"},
            {"id": "cell_3"},
        ]
        st.session_state["notebook_code_cell_1"] = "x = 21"
        st.session_state["notebook_code_cell_2"] = "print(x * 2)"
        st.session_state["notebook_code_cell_3"] = default_notebook_dataset_demo_code()

    st.session_state.setdefault("notebook_outputs", {})
    st.session_state.setdefault("notebook_cell_counter", len(st.session_state["notebook_cells"]))
    runtime = get_notebook_runtime()
    st.session_state["notebook_outputs"] = runtime["outputs"]


def default_notebook_dataset_demo_code() -> str:
    return '''import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("datasets/df_orders.csv")
display(df.head())

if {"category", "revenue"}.issubset(df.columns):
    df.groupby("category")["revenue"].sum().sort_values().plot(
        kind="barh",
        title="Revenue by category",
        figsize=(7, 4),
    )
    plt.tight_layout()
    plt.show()
'''


def add_notebook_cell() -> None:
    init_notebook_state()
    counter = int(st.session_state.get("notebook_cell_counter", 0)) + 1
    st.session_state["notebook_cell_counter"] = counter
    cell_id = f"cell_{counter}"
    st.session_state["notebook_cells"].append({"id": cell_id})
    st.session_state[f"notebook_code_{cell_id}"] = ""


def delete_notebook_cell(cell_id: str) -> None:
    init_notebook_state()
    st.session_state["notebook_cells"] = [
        cell for cell in st.session_state["notebook_cells"] if cell["id"] != cell_id
    ]
    runtime = get_notebook_runtime()
    runtime.setdefault("outputs", {}).pop(cell_id, None)
    st.session_state["notebook_outputs"] = runtime["outputs"]
    st.session_state.pop(f"notebook_code_{cell_id}", None)


def section_option_label(section_key: str, notes_count: int) -> str:
    return f"{humanize_section_name(section_key)} ({notes_count})"


def first_note_in_section(sections: dict[str, list[dict[str, str]]], section_key: str) -> str | None:
    notes = sections.get(section_key, [])
    return notes[0]["path"] if notes else None


def set_active_note(note: dict[str, str], push_history: bool = True) -> None:
    current_path = st.session_state.get("active_note_path")
    if push_history and current_path and current_path != note["path"]:
        history = st.session_state.setdefault("note_history", [])
        history.append(current_path)

    st.session_state["active_section"] = note["section_key"]
    st.session_state["active_note_path"] = note["path"]
    st.session_state["section_select"] = note["section_key"]
    st.session_state["note_radio"] = note["path"]
    st.session_state["note_search"] = ""


def go_back(note_index: dict[str, Any]) -> None:
    history = st.session_state.setdefault("note_history", [])
    note_by_path: dict[str, dict[str, str]] = note_index["note_by_path"]

    while history:
        previous_path = history.pop()
        previous_note = note_by_path.get(previous_path)
        if previous_note:
            set_active_note(previous_note, push_history=False)
            return


def on_section_change(sections: dict[str, list[dict[str, str]]]) -> None:
    section_key = st.session_state.get("section_select")
    if section_key not in sections:
        return

    st.session_state["active_section"] = section_key
    first_note_path = first_note_in_section(sections, section_key)
    if first_note_path:
        st.session_state["active_note_path"] = first_note_path
        st.session_state["note_radio"] = first_note_path


def on_note_change() -> None:
    selected_note_path = st.session_state.get("note_radio")
    if selected_note_path:
        st.session_state["active_note_path"] = selected_note_path


def ensure_active_state(sections: dict[str, list[dict[str, str]]]) -> None:
    section_keys = list(sections.keys())
    active_section = st.session_state.get("active_section")
    if active_section not in sections:
        active_section = section_keys[0]
        st.session_state["active_section"] = active_section

    section_note_paths = {note["path"] for note in sections[active_section]}
    active_note_path = st.session_state.get("active_note_path")
    if active_note_path not in section_note_paths:
        first_note_path = first_note_in_section(sections, active_section)
        if first_note_path:
            st.session_state["active_note_path"] = first_note_path

    st.session_state["section_select"] = st.session_state["active_section"]


def render_sidebar(sections: dict[str, list[dict[str, str]]]) -> tuple[str, dict[str, str] | None]:
    ensure_active_state(sections)

    st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
    st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
    st.sidebar.divider()
    st.sidebar.caption("Навигация по базе")

    section_keys = list(sections.keys())
    selected_section = st.sidebar.selectbox(
        "Раздел",
        section_keys,
        format_func=lambda key: section_option_label(key, len(sections[key])),
        key="section_select",
        on_change=on_section_change,
        args=(sections,),
    )

    query = st.sidebar.text_input("Поиск заметки", key="note_search").strip().casefold()
    notes = sections[selected_section]
    filtered_notes = [
        note for note in notes if not query or query in note["display_name"].casefold()
    ]

    if not filtered_notes:
        st.sidebar.info("Заметки не найдены")
        return selected_section, None

    filtered_paths = [note["path"] for note in filtered_notes]
    active_note_path = st.session_state.get("active_note_path")
    if active_note_path not in filtered_paths:
        active_note_path = filtered_paths[0]
        st.session_state["active_note_path"] = active_note_path

    st.session_state["note_radio"] = active_note_path
    selected_note_path = st.sidebar.radio(
        "Заметки",
        filtered_paths,
        format_func=lambda path: next(
            note["display_name"] for note in filtered_notes if note["path"] == path
        ),
        key="note_radio",
        on_change=on_note_change,
    )

    selected_note = next(note for note in filtered_notes if note["path"] == selected_note_path)
    st.session_state["active_section"] = selected_note["section_key"]
    st.session_state["active_note_path"] = selected_note["path"]
    return selected_note["section_key"], selected_note


def render_note_header(section_key: str, note: dict[str, str], frontmatter: dict[str, Any]) -> None:
    section_label = humanize_section_name(section_key)
    chips = render_frontmatter_chips(frontmatter)
    header = f"""
<div class="note-header">
    <div class="breadcrumbs">{html.escape(section_label)} / {html.escape(note["display_name"])}</div>
    {chips}
</div>
    """
    st.markdown(header, unsafe_allow_html=True)


def link_path_label(note: dict[str, str]) -> str:
    return f"{humanize_section_name(note['section_key'])} / {note['display_name']}"


def render_link_card(link: dict[str, Any], index: int, prefix: str) -> None:
    resolved_note = link.get("resolved_note")
    label = str(link.get("label") or link.get("target") or "")

    if resolved_note:
        suffix = " · неоднозначно" if link.get("status") == "ambiguous" else ""
        st.button(
            f"{label}{suffix}\n{link_path_label(resolved_note)}",
            key=f"{prefix}_{index}_{resolved_note['path']}_{label}",
            on_click=set_active_note,
            args=(resolved_note,),
            use_container_width=True,
        )
    else:
        st.button(
            f"{label} — не найдено",
            key=f"{prefix}_missing_{index}_{link.get('target')}",
            disabled=True,
            use_container_width=True,
        )


def dedupe_link_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        key = dedupe_link_key(record)
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def open_random_unstarted(sections: dict[str, list[dict[str, str]]]) -> None:
    candidates = [note for note in all_notes(sections) if get_note_status(note) == STATUS_NOT_STARTED]
    if not candidates:
        return
    set_active_note(random.choice(candidates), push_history=True)
    st.session_state["active_tab"] = "Theory"


def render_graph_navigation(
    note: dict[str, str],
    graph: dict[str, Any],
    sections: dict[str, list[dict[str, str]]],
) -> None:
    outgoing = dedupe_link_records(graph["outgoing_by_path"].get(note["path"], []))
    backlinks = dedupe_link_records(graph["backlinks_by_path"].get(note["path"], []))
    outgoing_found = [link for link in outgoing if link.get("resolved_note")]
    outgoing_missing = [link for link in outgoing if not link.get("resolved_note")]

    st.markdown('<div class="related-notes"><h3>🔗 Граф заметки</h3></div>', unsafe_allow_html=True)
    st.button(
        "🎲 Открыть случайную непройденную заметку",
        key="open_random_unstarted",
        on_click=open_random_unstarted,
        args=(sections,),
        use_container_width=True,
    )

    st.markdown("#### Исходящие ссылки")
    if outgoing_found:
        for index, link in enumerate(outgoing_found):
            render_link_card(link, index, "outgoing")
    else:
        st.caption("В этой заметке нет найденных исходящих ссылок.")

    if outgoing_missing:
        st.markdown("##### Не найдено")
        for index, link in enumerate(outgoing_missing):
            render_link_card(link, index, "outgoing_missing")

    st.markdown("#### Обратные ссылки / Backlinks")
    if backlinks:
        for index, link in enumerate(backlinks):
            source_note = link["source_note"]
            backlink_record = {
                **link,
                "label": link_path_label(source_note),
                "resolved_note": source_note,
                "status": "resolved",
            }
            render_link_card(backlink_record, index, "backlink")
    else:
        st.caption("Пока никто не ссылается на эту заметку.")


def render_learning_controls(note: dict[str, str]) -> None:
    status = get_note_status(note)
    note_key = note_progress_key(note)
    st.markdown(
        f"""
<div class="learning-panel">
    <div class="learning-panel-title">Учебный статус</div>
    <div class="muted-small">Отмечай состояние заметки, чтобы база становилась маршрутом, а не складом.</div>
    <div style="margin-top: 0.65rem;">{status_badge(status)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    status_buttons = [
        (STATUS_READING, "Читаю"),
        (STATUS_DONE, "Готово"),
        (STATUS_REPEAT, "Повторить"),
        (STATUS_NOT_STARTED, "Сбросить"),
    ]
    for col, (target_status, label) in zip(cols, status_buttons, strict=True):
        col.button(
            label,
            key=f"status_{target_status}_{note_key}",
            on_click=set_note_status_by_key,
            args=(note_key, target_status),
            use_container_width=True,
            disabled=status == target_status,
        )


def open_practice_card(card_id: str) -> None:
    st.session_state["selected_practice_card"] = card_id
    st.session_state["practice_filter_section"] = "Все"
    st.session_state["practice_filter_difficulty"] = "Все"
    st.session_state["active_tab"] = "🎯 Practice"


def open_theory_note(note: dict[str, str]) -> None:
    set_active_note(note, push_history=True)
    st.session_state["active_tab"] = "Theory"


def render_related_practice_block(
    note: dict[str, str],
    cards: list[dict[str, Any]],
    note_index: dict[str, Any],
) -> None:
    related_cards = cards_for_note(cards, note, note_index)
    if not related_cards:
        return

    st.markdown('<div class="related-notes"><h3>🎯 Практика по этой теме</h3></div>', unsafe_allow_html=True)
    for card in related_cards:
        st.markdown(
            f"""
<div class="today-card">
    <div class="today-card-title">{html.escape(card["title"])}</div>
    <div class="muted-small">
        {html.escape(card["section"])} · {html.escape(card["difficulty"])} · {html.escape(card["est_time"])}
    </div>
    <div style="margin-top: 0.45rem;">{practice_badge(get_card_status(card))}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Открыть карточку",
            key=f"related_practice_{card['id']}",
            on_click=open_practice_card,
            args=(card["id"],),
            use_container_width=True,
        )


def render_note(
    section_key: str,
    note: dict[str, str],
    vault: Path,
    note_index: dict[str, Any],
    graph: dict[str, Any],
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
) -> None:
    text, error = read_note(note["path"])
    if error:
        st.warning(f"Не удалось прочитать файл: {note['display_name']} ({error})")
        return

    frontmatter, body = split_frontmatter(text)
    render_note_header(section_key, note, frontmatter)
    render_learning_controls(note)

    if st.session_state.get("note_history"):
        st.button(
            "← Назад",
            key="back_button",
            on_click=go_back,
            args=(note_index,),
        )

    rendered_body = render_markdown_with_wikilinks(body)
    st.markdown(rendered_body, unsafe_allow_html=True)

    render_related_practice_block(note, practice_cards, note_index)
    render_graph_navigation(note, graph, sections)


def open_note_from_roadmap(note: dict[str, str]) -> None:
    set_active_note(note, push_history=False)
    st.session_state["active_tab"] = "Theory"


def open_tab(tab_name: str) -> None:
    st.session_state["active_tab"] = tab_name


def next_practice_card(cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    priority = {
        PRACTICE_DOING: 0,
        PRACTICE_TODO: 1,
        PRACTICE_DONE: 2,
    }
    candidates = [card for card in cards if get_card_status(card) != PRACTICE_DONE]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda card: (
            priority.get(get_card_status(card), 9),
            str(card["section"]).casefold(),
            str(card["title"]).casefold(),
        ),
    )[0]


def render_dashboard(
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    datasets: list[dict[str, Any]],
    graph: dict[str, Any],
) -> None:
    notes = all_notes(sections)
    total_notes = len(notes)
    done_notes = sum(1 for note in notes if get_note_status(note) == STATUS_DONE)
    reading_notes = sum(1 for note in notes if get_note_status(note) == STATUS_READING)
    practice_stats = practice_progress(practice_cards)
    output_stats = portfolio_progress(practice_cards)
    next_note = find_next_note(sections)
    next_card = next_practice_card(practice_cards)
    graph_summary = graph["summary"]

    st.markdown("### Home")
    st.markdown("Рабочий пульт: где ты сейчас, что делать дальше, и куда быстро перейти.")

    metric_cols = st.columns(5)
    metric_cols[0].metric("Заметки", f"{done_notes}/{total_notes}", f"{reading_notes} читаю")
    metric_cols[1].metric("Практика", f"{practice_stats[PRACTICE_DONE]}/{practice_stats['total']}")
    metric_cols[2].metric("Outputs", f"{output_stats['with_outputs']}/{output_stats['total']}")
    metric_cols[3].metric("Датасеты", len(datasets))
    metric_cols[4].metric("Битые ссылки", graph_summary["broken"])

    st.markdown("#### Следующий разумный шаг")
    step_cols = st.columns(2)
    with step_cols[0]:
        if next_note:
            st.markdown(
                f"""
<div class="learning-panel">
    <div class="learning-panel-title">Теория</div>
    <div class="muted-small">{html.escape(link_path_label(next_note))}</div>
    <div style="margin-top: 0.55rem;">{status_badge(get_note_status(next_note))}</div>
</div>
                """,
                unsafe_allow_html=True,
            )
            st.button(
                "Открыть заметку",
                key="home_open_next_note",
                on_click=open_note_from_roadmap,
                args=(next_note,),
                use_container_width=True,
            )
        else:
            st.success("Все заметки закрыты по статусу.")

    with step_cols[1]:
        if next_card:
            st.markdown(
                f"""
<div class="learning-panel">
    <div class="learning-panel-title">Практика</div>
    <div class="muted-small">{html.escape(next_card["section"])} · {html.escape(next_card["difficulty"])} · {html.escape(next_card["est_time"])}</div>
    <div style="margin-top: 0.35rem;">{html.escape(next_card["title"])}</div>
    <div style="margin-top: 0.55rem;">{practice_badge(get_card_status(next_card))}</div>
</div>
                """,
                unsafe_allow_html=True,
            )
            st.button(
                "Открыть карточку",
                key="home_open_next_card",
                on_click=open_practice_card,
                args=(next_card["id"],),
                use_container_width=True,
            )
        else:
            st.success("Все карточки практики готовы.")

    st.markdown("#### Быстрые переходы")
    quick_links = [
        ("Theory", "Theory"),
        ("Practice", "🎯 Practice"),
        ("Tasks", "🎯 Tasks"),
        ("Portfolio", "📁 Portfolio"),
        ("Datasets", "📊 Datasets"),
        ("Scratch", "⚡ Scratch"),
        ("Notebook", "📓 Notebook"),
        ("Algorithms", "🧩 Algorithms"),
        ("Interviews", "🎤 Interviews"),
        ("Architecture", "🏗 Architecture"),
        ("Quality", "🧭 Theory Quality"),
        ("Roadmap", "Roadmap"),
        ("Links", "🔗 Links Health"),
    ]
    quick_cols = st.columns(len(quick_links))
    for col, (label, tab_name) in zip(quick_cols, quick_links, strict=True):
        col.button(
            label,
            key=f"home_tab_{tab_name}",
            on_click=open_tab,
            args=(tab_name,),
            use_container_width=True,
        )

    st.markdown("#### Разделы базы")
    for section_key, section_notes in sections.items():
        stats = section_progress(section_notes)
        total = stats["total"]
        ratio = stats[STATUS_DONE] / total if total else 0.0
        st.markdown(
            f"""
<div class="section-progress-row">
    <strong>{html.escape(humanize_section_name(section_key))}</strong>
    <div class="muted-small">
        {stats[STATUS_DONE]}/{total} готово · {stats[STATUS_READING]} читаю · {stats[STATUS_REPEAT]} повторить
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(ratio)


def render_roadmap(sections: dict[str, list[dict[str, str]]]) -> None:
    st.markdown("### Roadmap")
    st.markdown(
        "Это учебная карта поверх Obsidian: проходи разделы, открывай заметки и отмечай прогресс."
    )

    next_note = find_next_note(sections)
    if next_note:
        section_label = humanize_section_name(next_note["section_key"])
        st.markdown(
            f"""
<div class="learning-panel">
    <div class="learning-panel-title">Следующий разумный шаг</div>
    <div class="muted-small">{html.escape(section_label)} / {html.escape(next_note["display_name"])}</div>
    <div style="margin-top: 0.5rem;">{status_badge(get_note_status(next_note))}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Открыть следующую заметку",
            key="open_next_note",
            on_click=open_note_from_roadmap,
            args=(next_note,),
            use_container_width=True,
        )
    else:
        st.success("Все заметки отмечены как готовые. Красиво идем.")

    for section_key, notes in sections.items():
        stats = section_progress(notes)
        done = stats[STATUS_DONE]
        reading = stats[STATUS_READING]
        repeat = stats[STATUS_REPEAT]
        total = stats["total"]
        ratio = done / total if total else 0.0

        st.markdown(
            f"""
<div class="roadmap-card">
    <div class="roadmap-title">{html.escape(humanize_section_name(section_key))}</div>
    <div class="roadmap-meta">
        {done}/{total} готово · {reading} читаю · {repeat} повторить
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(ratio)

        with st.expander(f"Заметки раздела: {humanize_section_name(section_key)}"):
            for note in notes:
                cols = st.columns([0.52, 0.22, 0.26])
                cols[0].markdown(
                    f"{html.escape(note['display_name'])}",
                    unsafe_allow_html=True,
                )
                cols[1].markdown(status_badge(get_note_status(note)), unsafe_allow_html=True)
                cols[2].button(
                    "Открыть",
                    key=f"roadmap_open_{note['relative_path']}",
                    on_click=open_note_from_roadmap,
                    args=(note,),
                    use_container_width=True,
                )


def render_external_links(links: list[str]) -> None:
    if not links:
        return

    rendered = []
    for index, url in enumerate(links, start=1):
        safe_url = html.escape(url, quote=True)
        rendered.append(
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">Ресурс {index}</a>'
        )
    st.markdown(
        '<div class="frontmatter-row">' + "".join(f'<span class="fm-chip">{item}</span>' for item in rendered) + "</div>",
        unsafe_allow_html=True,
    )


def render_practice_card_summary(card: dict[str, Any]) -> None:
    dataset = f" · dataset: {card['dataset']}" if card.get("dataset") else ""
    st.markdown(
        f"""
<div class="today-card">
    <div class="today-card-title">{html.escape(card["title"])}</div>
    <div class="muted-small">
        {html.escape(card["section"])} · {html.escape(card["difficulty"])} ·
        {html.escape(card["est_time"])}{html.escape(dataset)}
    </div>
    <div style="margin-top: 0.45rem;">{practice_badge(get_card_status(card))}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def select_practice_card(card_id: str) -> None:
    st.session_state["selected_practice_card"] = card_id


def render_portfolio_output_form(card: dict[str, Any]) -> None:
    card_id = card["id"]
    record = get_output_record(card_id)
    base_key = safe_widget_key("portfolio_output", card_id)
    flash_key = f"{base_key}_flash"
    flash_message = st.session_state.pop(flash_key, "")

    version_map = st.session_state.setdefault("portfolio_output_versions", {})
    if not isinstance(version_map, dict):
        version_map = {}
        st.session_state["portfolio_output_versions"] = version_map
    version = int(version_map.get(card_id, 0) or 0)
    if flash_message == "cleared":
        version += 1
        version_map[card_id] = version

    key_prefix = f"{base_key}_{version}"
    summary_key = f"{key_prefix}_summary"
    artifact_key = f"{key_prefix}_artifact"
    reflection_key = f"{key_prefix}_reflection"

    st.session_state.setdefault(summary_key, str(record.get("summary", "")))
    st.session_state.setdefault(artifact_key, str(record.get("artifact", "")))
    st.session_state.setdefault(reflection_key, str(record.get("reflection", "")))

    st.markdown("#### Portfolio output")
    if flash_message == "saved":
        st.success("Output сохранён.")
    st.markdown(
        """
<div class="practice-panel">
    <div class="practice-title">Что останется после задачи</div>
    <div class="muted-small">Коротко зафиксируй результат, путь к артефакту и вывод. Это не проверка, а след работы.</div>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.text_area("Что сделал", key=summary_key, height=90)
    st.text_input("Ссылка или путь к артефакту", key=artifact_key)
    st.text_area("Вывод / следующий шаг", key=reflection_key, height=90)

    cols = st.columns(2)
    if cols[0].button("Сохранить output", key=f"{key_prefix}_save", use_container_width=True):
        save_output_record(
            card_id,
            st.session_state.get(summary_key, ""),
            st.session_state.get(artifact_key, ""),
            st.session_state.get(reflection_key, ""),
        )
        st.session_state[flash_key] = "saved"
        st.rerun()
    if cols[1].button(
        "Очистить output",
        key=f"{key_prefix}_clear",
        use_container_width=True,
        disabled=not output_has_content(record),
    ):
        clear_output_record(card_id)
        st.session_state[flash_key] = "cleared"
        st.rerun()


def render_practice_detail(
    card: dict[str, Any],
    note_index: dict[str, Any],
    datasets: list[dict[str, Any]],
) -> None:
    chips = {
        "section": card["section"],
        "difficulty": card["difficulty"],
        "est_time": card["est_time"],
    }
    if card.get("dataset"):
        chips["dataset"] = card["dataset"]

    st.markdown(f"### {card['title']}")
    st.markdown(render_frontmatter_chips(chips), unsafe_allow_html=True)
    render_external_links(card.get("links", []))

    related_note = resolve_related_note(str(card.get("related_note") or ""), note_index)
    if related_note:
        st.button(
            "📖 Открыть теорию",
            key=f"practice_open_theory_{card['id']}",
            on_click=open_theory_note,
            args=(related_note,),
            use_container_width=True,
        )
    elif card.get("related_note"):
        st.warning(f"Связанная заметка не найдена: {card['related_note']}")

    if card.get("dataset"):
        dataset = find_dataset_record(card["dataset"], datasets)
        st.button(
            "📊 Открыть датасет",
            key=f"practice_open_dataset_{card['id']}",
            on_click=open_dataset_from_card,
            args=(card["dataset"], card["id"]),
            use_container_width=True,
            disabled=dataset is None,
        )
        st.button(
            "📓 Открыть в Notebook",
            key=f"practice_open_notebook_{card['id']}",
            on_click=open_dataset_in_notebook,
            args=(card["dataset"],),
            use_container_width=True,
            disabled=dataset is None,
        )
        if dataset is None:
            st.caption(f"Файл {card['dataset']} пока не найден в datasets/.")

    st.markdown(card["body"], unsafe_allow_html=False)

    status = get_card_status(card)
    cols = st.columns(3)
    cols[0].button(
        "В работу",
        key=f"card_doing_{card['id']}",
        on_click=set_card_status,
        args=(card["id"], PRACTICE_DOING),
        use_container_width=True,
        disabled=status == PRACTICE_DOING,
    )
    cols[1].button(
        "Сделано",
        key=f"card_done_{card['id']}",
        on_click=set_card_status,
        args=(card["id"], PRACTICE_DONE),
        use_container_width=True,
        disabled=status == PRACTICE_DONE,
    )
    cols[2].button(
        "Сбросить",
        key=f"card_reset_{card['id']}",
        on_click=set_card_status,
        args=(card["id"], PRACTICE_TODO),
        use_container_width=True,
        disabled=status == PRACTICE_TODO,
    )

    render_portfolio_output_form(card)


def render_practice_tab(
    cards: list[dict[str, Any]],
    warnings: list[str],
    note_index: dict[str, Any],
    datasets: list[dict[str, Any]],
) -> None:
    st.markdown("### 🎯 Practice")
    st.markdown(
        "Карточки превращают теорию в действие: инструкция, ресурсы, самопроверка и портфолио-выход."
    )

    for warning in warnings:
        st.warning(warning)

    if not cards:
        st.info("Папка practice/ пуста или пока не создана. Добавьте markdown-карточки рядом с приложением.")
        return

    stats = practice_progress(cards)
    metric_cols = st.columns(3)
    metric_cols[0].metric("Карточек", stats["total"])
    metric_cols[1].metric("В работе", stats[PRACTICE_DOING])
    metric_cols[2].metric("Сделано", stats[PRACTICE_DONE])

    sections = ["Все"] + sorted({card["section"] for card in cards}, key=str.casefold)
    difficulties = ["Все", "easy", "medium", "hard"]
    filter_cols = st.columns(2)
    selected_section = filter_cols[0].selectbox("Section", sections, key="practice_filter_section")
    selected_difficulty = filter_cols[1].selectbox("Difficulty", difficulties, key="practice_filter_difficulty")

    filtered = [
        card
        for card in cards
        if (selected_section == "Все" or card["section"] == selected_section)
        and (selected_difficulty == "Все" or card["difficulty"] == selected_difficulty)
    ]

    if not filtered:
        st.info("По таким фильтрам карточек нет.")
        return

    selected_id = st.session_state.get("selected_practice_card")
    if selected_id not in {card["id"] for card in filtered}:
        selected_id = filtered[0]["id"]
        st.session_state["selected_practice_card"] = selected_id

    list_col, detail_col = st.columns([0.38, 0.62], gap="large")
    with list_col:
        st.markdown("#### Карточки")
        for card in filtered:
            render_practice_card_summary(card)
            st.button(
                "Открыть",
                key=f"practice_select_{card['id']}",
                on_click=select_practice_card,
                args=(card["id"],),
                use_container_width=True,
            )

    selected_card = next(card for card in filtered if card["id"] == st.session_state["selected_practice_card"])
    with detail_col:
        render_practice_detail(selected_card, note_index, datasets)


def artifact_markup(artifact: str) -> str:
    value = artifact.strip()
    if not value:
        return ""
    safe_value = html.escape(value)
    if value.startswith(("http://", "https://")):
        return f'<a href="{html.escape(value, quote=True)}" target="_blank" rel="noopener noreferrer">{safe_value}</a>'
    return safe_value


def render_portfolio_tab(cards: list[dict[str, Any]]) -> None:
    st.markdown("### 📁 Portfolio")
    st.markdown("Здесь собираются результаты практики: артефакты, выводы и следы работы, которые потом можно превращать в резюме и GitHub.")

    if not cards:
        st.info("Пока нет карточек практики, поэтому портфолио пустое.")
        return

    practice_stats = practice_progress(cards)
    output_stats = portfolio_progress(cards)
    metric_cols = st.columns(3)
    metric_cols[0].metric("Output записан", f"{output_stats['with_outputs']}/{output_stats['total']}")
    metric_cols[1].metric("Практика сделана", f"{practice_stats[PRACTICE_DONE]}/{practice_stats['total']}")
    metric_cols[2].metric("Без output", output_stats["missing"])

    output_ratio = output_stats["with_outputs"] / output_stats["total"] if output_stats["total"] else 0.0
    st.progress(output_ratio)

    view = st.radio(
        "Показать",
        ["Все", "Есть output", "Нет output"],
        key="portfolio_filter",
        horizontal=True,
    )
    filtered: list[dict[str, Any]] = []
    for card in cards:
        has_output = card_has_output(card)
        if view == "Есть output" and not has_output:
            continue
        if view == "Нет output" and has_output:
            continue
        filtered.append(card)

    if not filtered:
        st.info("По этому фильтру ничего нет.")
        return

    for card in filtered:
        record = get_output_record(card["id"])
        has_output = output_has_content(record)
        summary = str(record.get("summary", "")).strip()
        artifact = str(record.get("artifact", "")).strip()
        reflection = str(record.get("reflection", "")).strip()
        updated_at = str(record.get("updated_at", "")).strip()

        st.markdown(
            f"""
<div class="today-card">
    <div class="today-card-title">{html.escape(card["title"])}</div>
    <div class="muted-small">
        {html.escape(card["section"])} · {html.escape(card["difficulty"])} · {html.escape(card["est_time"])}
    </div>
    <div style="margin-top: 0.45rem;">
        {practice_badge(get_card_status(card))}
        <span class="status-pill {'status-done' if has_output else 'status-not-started'}">
            {'■ output есть' if has_output else '□ output пустой'}
        </span>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

        if has_output:
            details = []
            if summary:
                details.append(f"<strong>Сделано:</strong> {html.escape(summary)}")
            if artifact:
                details.append(f"<strong>Артефакт:</strong> {artifact_markup(artifact)}")
            if reflection:
                details.append(f"<strong>Вывод:</strong> {html.escape(reflection)}")
            if updated_at:
                details.append(f'<span class="muted-small">Обновлено: {html.escape(updated_at[:19].replace("T", " "))}</span>')
            st.markdown(
                '<div class="practice-output">' + "<br>".join(details) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Открой карточку и заполни output, когда появится результат.")

        st.button(
            "Открыть карточку",
            key=f"portfolio_open_{card['id']}",
            on_click=open_practice_card,
            args=(card["id"],),
            use_container_width=True,
        )


def render_algorithm_result(result: dict[str, Any]) -> None:
    elapsed = float(result.get("elapsed") or 0.0)
    if result.get("timed_out"):
        st.error(f"⏱ Таймаут после {elapsed:.2f} сек. Процесс остановлен.")
    elif result.get("exit_code") == 0:
        st.success(f"✅ Все тесты прошли за {elapsed:.2f} сек.")
    else:
        st.error(f"❌ Тесты упали. Exit code: {result.get('exit_code')}")

    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()
    if stdout:
        st.markdown("**stdout**")
        st.code(stdout, language="text")
    if stderr:
        st.markdown("**stderr / traceback**")
        st.code(stderr, language="text")
    if not stdout and not stderr:
        st.caption("Процесс не вернул stdout/stderr.")


def render_algorithms_tab(lessons: list[dict[str, Any]]) -> None:
    st.markdown("### 🧩 Algorithms Lab")
    st.markdown(
        "Livecoding-тренажер по файлам ментора: теория из docstring, эталонный код и запуск встроенных assert-тестов."
    )

    if not lessons:
        st.info("Папка algos_patterns/ не найдена или в ней нет .py уроков.")
        return

    stats = algorithm_progress(lessons)
    metric_cols = st.columns(3)
    metric_cols[0].metric("Уроков", stats["total"])
    metric_cols[1].metric("Пройдено", stats["done"])
    metric_cols[2].metric("Осталось", stats["todo"])

    lesson_ids = [lesson["id"] for lesson in lessons]
    selected_id = st.session_state.get("selected_algorithm_lesson")
    if selected_id not in lesson_ids:
        selected_id = lesson_ids[0]
        st.session_state["selected_algorithm_lesson"] = selected_id

    selected_id = st.selectbox(
        "Урок",
        lesson_ids,
        key="selected_algorithm_lesson",
        format_func=lambda lesson_id: next(
            f"{lesson['title']} ({lesson['id']})" for lesson in lessons if lesson["id"] == lesson_id
        ),
    )
    lesson = next(item for item in lessons if item["id"] == selected_id)
    status = get_algorithm_status(lesson["id"])

    st.markdown(
        f"""
<div class="today-card">
    <div class="today-card-title">{html.escape(lesson["title"])}</div>
    <div class="muted-small">{html.escape(lesson["id"])}</div>
    <div style="margin-top: 0.45rem;">{status_badge(status)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    if lesson.get("error"):
        st.warning(f"Файл не удалось прочитать: {lesson['error']}")
        return

    st.markdown("#### Теория")
    docstring = str(lesson.get("docstring") or "").strip()
    if docstring:
        st.markdown(f"```text\n{docstring}\n```")
    else:
        st.info("Верхний модульный docstring не найден.")

    with st.expander("Эталонный код", expanded=False):
        st.code(str(lesson.get("code") or ""), language="python")

    result_key = f"algorithm_result_{lesson['id']}"
    if st.button("▶ Прогнать тесты", key=f"run_algorithm_{lesson['id']}", use_container_width=True):
        with st.spinner("Запускаю файл и встроенные assert-проверки..."):
            result = run_algorithm_tests(lesson["path"])
        st.session_state[result_key] = result
        if result.get("exit_code") == 0 and not result.get("timed_out"):
            set_algorithm_status(lesson["id"], STATUS_DONE, result)

    if result_key in st.session_state:
        render_algorithm_result(st.session_state[result_key])


def select_mentor_task(task_id: str) -> None:
    st.session_state["selected_mentor_task"] = task_id


def mentor_task_badge(task: dict[str, Any]) -> str:
    status = get_mentor_task_status(task["id"])
    confidence = str(task["confidence"])
    confidence_class = "status-repeat" if confidence == "low" else "status-reading"
    confidence_label = "требует ревью" if confidence == "low" else confidence
    return (
        status_badge(status)
        + " "
        + f'<span class="status-pill {confidence_class}">{html.escape(confidence_label)}</span>'
    )


def render_mentor_task_summary(task: dict[str, Any]) -> None:
    st.markdown(
        f"""
<div class="today-card">
    <div class="today-card-title">{html.escape(task["title"])}</div>
    <div class="muted-small">{html.escape(task["notebook_label"])} · {html.escape(task["source_notebook"])}</div>
    <div style="margin-top: 0.45rem;">{mentor_task_badge(task)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_mentor_task_result(result: dict[str, Any]) -> None:
    classification = str(result.get("classification") or classify_task_result(result))
    elapsed = float(result.get("elapsed") or 0)

    if classification == "PASS":
        st.success(f"✅ Решено · {float(result.get('elapsed') or 0):.2f}s")
    elif classification == "FAIL":
        st.error(f"❌ FAIL · {elapsed:.2f}s")
        st.caption("Код запустился, но ожидаемые значения не совпали с assert-проверками.")
    elif classification == "ERROR":
        st.error(f"💥 ERROR · {elapsed:.2f}s")
        st.caption("Код упал до прохождения проверок. Исправьте runtime-ошибку и запустите снова.")
    elif classification == "TIMEOUT":
        st.error(f"⏱ TIMEOUT · {elapsed:.2f}s")
        st.caption("Выполнение заняло слишком много времени и было прервано.")
    elif classification == "KERNEL_BUSY":
        st.warning("⏳ KERNEL_BUSY")
        st.caption("Jupyter-ядро уже выполняет другую ячейку или задачу.")
    else:
        st.error(f"❌ {classification or 'UNKNOWN'} · {elapsed:.2f}s")

    stdout = str(result.get("stdout") or "")
    if stdout:
        st.markdown("#### stdout")
        st.code(stdout, language="text")

    outputs = result.get("outputs", [])
    errors = [output for output in outputs if isinstance(output, dict) and output.get("type") == "error"]
    if errors:
        st.markdown("#### Ошибка / traceback")
        for output in errors:
            ename = str(output.get("ename") or "Error")
            evalue = str(output.get("evalue") or "")
            st.caption(f"{ename}: {evalue}".strip())
            with st.expander("Показать traceback", expanded=False):
                text = traceback_text(output)
                st.code(text or str(output), language="text")
    elif not stdout:
        st.caption("Код не напечатал stdout, но assert-проверки прошли.")


def render_mentor_task_detail(task: dict[str, Any]) -> None:
    code_key = f"mentor_task_code_{task['id']}"
    result_key = f"mentor_task_result_{task['id']}"
    if code_key not in st.session_state:
        st.session_state[code_key] = task["solution_starter"]

    left_col, right_col = st.columns([0.45, 0.55], gap="large")
    with left_col:
        st.markdown("#### Условие")
        st.caption(f"{task['notebook_label']} / {task['source_notebook']} · cell {task.get('code_cell_index')}")
        st.markdown(task["prompt"])
        dataset_snippet = dataset_snippet_for_task(task)
        if dataset_snippet:
            with st.expander("Dataset snippet", expanded=False):
                st.caption("Относительные пути от корня проекта. Можно использовать в решении или Notebook.")
                st.code(dataset_snippet, language="python")
        if task.get("dependency_hint"):
            st.warning(task["dependency_hint"])
            if task.get("setup_code"):
                with st.expander("Setup, который будет добавлен перед проверкой", expanded=False):
                    st.code(task["setup_code"], language="python")
        with st.expander("Assert-проверки", expanded=False):
            st.code("\n".join(task["tests"]), language="python")

    with right_col:
        st.markdown("#### Решение")
        use_plain_editor = st.session_state.get("tasks_plain_editor", False) or st_ace is None
        if st_ace is not None and not use_plain_editor:
            code = st_ace(
                value=st.session_state[code_key],
                language="python",
                theme="tomorrow_night",
                min_lines=16,
                max_lines=32,
                key=f"mentor_task_editor_{task['id']}",
            )
            if code is not None:
                st.session_state[code_key] = code
        else:
            st.text_area("Python code", height=420, key=code_key)

        button_cols = st.columns(2)
        if button_cols[0].button("▶ Проверить", key=f"check_mentor_task_{task['id']}", use_container_width=True):
            final_script = build_mentor_task_script(
                st.session_state.get(code_key, ""),
                task["test_code"],
                task.get("setup_code", ""),
            )
            with st.spinner("Запускаю в Jupyter-ядре и проверяю assert..."):
                result = run_code_in_notebook_kernel_sync(final_script)
            st.session_state[result_key] = result
            if classify_task_result(result) == "PASS":
                set_mentor_task_status(task["id"], STATUS_DONE, result)

        if button_cols[1].button("Сбросить код", key=f"reset_mentor_task_{task['id']}", use_container_width=True):
            st.session_state[code_key] = task["solution_starter"]
            st.rerun()

        if result_key in st.session_state:
            render_mentor_task_result(st.session_state[result_key])


def render_tasks_tab(mentor_data: dict[str, Any]) -> None:
    st.markdown("### 🎯 Tasks")
    st.markdown("Автопроверяемые задачи из ноутбуков ментора. В работу берутся только задания с `assert`.")

    tasks = mentor_data.get("tasks", [])
    if not tasks:
        st.info("Файл `content/extracted/mentor_tasks.json` не найден или в нём нет автопроверяемых задач.")
        return

    normal_tasks = [task for task in tasks if task["confidence"] in {"high", "medium"}]
    review_tasks = [task for task in tasks if task["confidence"] == "low"]
    stats = mentor_tasks_progress(tasks)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Автозадач", len(tasks))
    metric_cols[1].metric("В работе", len(normal_tasks))
    metric_cols[2].metric("Решено", f"{stats['done']}/{stats['total']}")
    metric_cols[3].metric("На ревью", len(review_tasks))

    notebook_options = ["Все"] + sorted({task["notebook_label"] for task in normal_tasks}, key=str.casefold)
    confidence_options = ["Все", "high", "medium"]
    filter_cols = st.columns(3)
    selected_notebook = filter_cols[0].selectbox("Notebook", notebook_options, key="mentor_task_notebook_filter")
    selected_confidence = filter_cols[1].selectbox("Confidence", confidence_options, key="mentor_task_confidence_filter")
    filter_cols[2].checkbox("Простой редактор", key="tasks_plain_editor")

    filtered = [
        task
        for task in normal_tasks
        if (selected_notebook == "Все" or task["notebook_label"] == selected_notebook)
        and (selected_confidence == "Все" or task["confidence"] == selected_confidence)
    ]

    selected_id = st.session_state.get("selected_mentor_task")
    visible_ids = {task["id"] for task in filtered}
    if filtered and selected_id not in visible_ids:
        selected_id = filtered[0]["id"]
        st.session_state["selected_mentor_task"] = selected_id

    if not filtered:
        st.info("По этим фильтрам задач нет.")
    else:
        list_col, detail_col = st.columns([0.36, 0.64], gap="large")
        with list_col:
            current_group = ""
            for task in filtered:
                if task["notebook_label"] != current_group:
                    current_group = task["notebook_label"]
                    st.markdown(f"#### {html.escape(current_group)}")
                render_mentor_task_summary(task)
                st.button(
                    "Открыть",
                    key=f"mentor_task_select_{task['id']}",
                    on_click=select_mentor_task,
                    args=(task["id"],),
                    use_container_width=True,
                )

        selected_task = next(task for task in filtered if task["id"] == st.session_state["selected_mentor_task"])
        with detail_col:
            render_mentor_task_detail(selected_task)

    with st.expander(f"Требует ревью ({len(review_tasks)})", expanded=False):
        if not review_tasks:
            st.caption("Low-confidence задач нет.")
        for task in review_tasks:
            render_mentor_task_summary(task)
            st.code(task["starter_code"], language="python")


def render_interviews_tab(interview_data: dict[str, Any]) -> None:
    st.markdown("### 🎤 Interviews")
    st.markdown("Вопросы и задачи с ML/DS собеседований, сгруппированные по компаниям.")

    companies = interview_data.get("companies", [])
    if not companies:
        st.info("Файл с вопросами пока не найден или не распарсился.")
        return

    metric_cols = st.columns(3)
    metric_cols[0].metric("Компаний", interview_data.get("total_companies", len(companies)))
    metric_cols[1].metric("Вопросов", interview_data.get("total_questions", 0))
    metric_cols[2].metric("Задач", interview_data.get("total_tasks", 0))

    company_names = ["Все"] + [entry["company"] for entry in companies]
    filter_cols = st.columns([0.45, 0.55])
    selected_company = filter_cols[0].selectbox("Компания", company_names, key="interview_company_filter")
    query = filter_cols[1].text_input("Поиск по вопросам", key="interview_search").strip().casefold()

    filtered: list[dict[str, Any]] = []
    for entry in companies:
        if selected_company != "Все" and entry["company"] != selected_company:
            continue
        haystack = " ".join(
            [entry["company"], *entry.get("questions", []), *entry.get("tasks", []), *entry.get("notes", [])]
        ).casefold()
        if query and query not in haystack:
            continue
        filtered.append(entry)

    if not filtered:
        st.info("По такому фильтру вопросов нет.")
        return

    for entry in filtered:
        questions = entry.get("questions", [])
        tasks = entry.get("tasks", [])
        relevance = entry.get("relevance", "")
        with st.expander(
            f"{entry['company']} · {len(questions)} вопросов · {len(tasks)} задач",
            expanded=selected_company != "Все",
        ):
            if relevance:
                st.caption(f"Актуальность: {relevance}")
            if questions:
                st.markdown("#### Вопросы")
                for index, question in enumerate(questions, start=1):
                    st.markdown(f"{index}. {question}")
            if tasks:
                st.markdown("#### Задачи")
                for task in tasks:
                    st.markdown(task)
            if entry.get("notes"):
                st.markdown("#### Дополнительно")
                for note in entry["notes"]:
                    st.markdown(f"- {note}")


def render_architecture_tab(architecture_data: dict[str, Any]) -> None:
    st.markdown("### 🏗 Architecture")
    st.markdown("Отдельный учебный справочник по архитектурным принципам и trade-offs.")

    document_html = str(architecture_data.get("html") or "")
    sections = architecture_data.get("sections", [])
    if not document_html:
        st.info("Материал по архитектуре пока не найден.")
        return

    metric_cols = st.columns(2)
    metric_cols[0].metric("Документ", architecture_data.get("title", "Architecture"))
    metric_cols[1].metric("Разделов", len(sections))

    section_titles = ["Весь документ"] + [section["title"] for section in sections]
    control_cols = st.columns([0.5, 0.5])
    selected_title = control_cols[0].selectbox("Раздел", section_titles, key="architecture_section")
    query = control_cols[1].text_input("Поиск по названиям разделов", key="architecture_search").strip().casefold()

    if query:
        matches = [section for section in sections if query in section["title"].casefold()]
        if matches:
            st.caption("Найденные разделы: " + " · ".join(section["title"] for section in matches[:8]))
        else:
            st.warning("По названиям разделов ничего не найдено.")

    if selected_title == "Весь документ":
        html_to_render = document_html
    else:
        selected = next((section for section in sections if section["title"] == selected_title), None)
        html_to_render = selected["html"] if selected else document_html

    st.markdown(
        """
<style>
    .architecture-doc {
        max-width: 860px;
        margin: 0 auto;
        line-height: 1.68;
        font-size: 16px;
    }
    .architecture-doc h2,
    .architecture-doc h3,
    .architecture-doc h4 {
        margin-top: 1.35rem;
        margin-bottom: 0.65rem;
    }
    .architecture-doc details {
        border: 1px solid var(--ls-border);
        border-radius: 8px;
        padding: 0.65rem 0.8rem;
        margin: 0.75rem 0;
        background: var(--ls-softer);
    }
    .architecture-doc summary {
        cursor: pointer;
        font-weight: 650;
    }
    .architecture-doc blockquote {
        border-left: 3px solid var(--ls-link);
        padding-left: 0.9rem;
        color: var(--ls-muted);
    }
    .architecture-doc code {
        background: var(--ls-code-bg);
        border-radius: 5px;
        padding: 0.08rem 0.28rem;
    }
</style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="architecture-doc">{html_to_render}</div>', unsafe_allow_html=True)


def note_from_relative_path(relative_path: str, note_index: dict[str, Any]) -> dict[str, str] | None:
    wanted = str(relative_path or "").strip().casefold()
    if not wanted:
        return None
    for note in note_index.get("all_notes", []):
        if str(note.get("relative_path", "")).casefold() == wanted:
            return note
    return None


def render_theory_quality_tab(note_index: dict[str, Any]) -> None:
    st.markdown("### 🧭 Theory Quality")
    st.markdown(
        "Read-only срез качества базы знаний. Он использует готовые отчёты и не сканирует vault автоматически."
    )

    audit_report = load_json_report(THEORY_AUDIT_REPORT_PATH)
    coverage_report = load_json_report(COVERAGE_REPORT_PATH)
    audit_summary = theory_summary(audit_report)
    cov_summary = coverage_summary(coverage_report)

    with st.expander("Как обновить отчёты вручную", expanded=not audit_report):
        st.markdown(
            """
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/audit_theory_notes.py --vault "$VAULT_PATH"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/check_coverage.py --vault "$VAULT_PATH"
```

Если `VAULT_PATH` не задан, подставь абсолютный путь к Obsidian vault через `--vault`.
            """
        )

    if not audit_report:
        st.warning(f"Не найден отчёт: `{THEORY_AUDIT_REPORT_PATH}`")
        return

    meta_cols = st.columns(4)
    meta_cols[0].metric("Заметок", audit_summary.get("total_notes", 0))
    meta_cols[1].metric("Средний score", audit_summary.get("average_quality_score", "—"))
    meta_cols[2].metric("Без examples", len(audit_summary.get("notes_without_examples", []) or []))
    meta_cols[3].metric("Без sources", len(audit_summary.get("notes_without_sources", []) or []))

    if audit_summary.get("generated_at"):
        st.caption(f"Theory audit generated: {audit_summary['generated_at']}")
    if audit_report.get("vault"):
        st.caption(f"Vault: {audit_report['vault']}")

    st.markdown("#### Weakest Notes")
    weak = weakest_notes(audit_report, limit=20)
    if not weak:
        st.info("Weakest notes не найдены в отчёте.")
    else:
        for index, note in enumerate(weak):
            relative_path = str(note.get("relative_path") or "")
            title = str(note.get("title") or relative_path)
            score = note.get("quality_score", "—")
            words = note.get("word_count", "—")
            section = str(note.get("section") or "")
            st.markdown(
                f"""
<div class="health-row">
    <div class="link-label">{html.escape(title)}</div>
    <div class="link-path">{html.escape(relative_path)}</div>
    <div class="link-path">score: {html.escape(str(score))} · words: {html.escape(str(words))} · {html.escape(section)}</div>
</div>
                """,
                unsafe_allow_html=True,
            )
            target_note = note_from_relative_path(relative_path, note_index)
            if target_note:
                st.button(
                    "Открыть в Theory",
                    key=f"quality_open_weak_{index}_{relative_path}",
                    on_click=open_theory_note,
                    args=(target_note,),
                    use_container_width=True,
                )

    list_cols = st.columns(2)
    with list_cols[0]:
        st.markdown("#### Notes Without Examples")
        examples_missing = report_list(audit_summary, "notes_without_examples", limit=30)
        if examples_missing:
            st.markdown("\n".join(f"- `{path}`" for path in examples_missing))
        else:
            st.success("Все заметки имеют examples по текущей эвристике.")

    with list_cols[1]:
        st.markdown("#### Notes Without Sources")
        sources_missing = report_list(audit_summary, "notes_without_sources", limit=30)
        if sources_missing:
            st.markdown("\n".join(f"- `{path}`" for path in sources_missing))
        else:
            st.success("Все заметки имеют sources по текущей эвристике.")

    st.markdown("#### Coverage")
    if not coverage_report:
        st.info(f"Coverage report не найден: `{COVERAGE_REPORT_PATH}`")
        return

    if cov_summary.get("generated_at"):
        st.caption(f"Coverage report generated: {cov_summary['generated_at']}")

    missing = missing_required_topics(coverage_report)
    if missing:
        st.markdown("##### Missing Required Topics")
        st.dataframe(
            [
                {
                    "track": topic.get("track"),
                    "level": topic.get("level"),
                    "id": topic.get("id"),
                    "title": topic.get("title"),
                    "status": topic.get("status"),
                }
                for topic in missing
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("Missing required topics не найдены в coverage report.")

    track_rows = []
    for track, counts in coverage_by_track(coverage_report).items():
        track_rows.append(
            {
                "track": track,
                "covered": counts.get("covered", 0),
                "partial": counts.get("partial", 0),
                "theory_only": counts.get("theory_only", 0),
                "practice_only": counts.get("practice_only", 0),
                "missing": counts.get("missing", 0),
            }
        )
    if track_rows:
        st.markdown("##### Coverage By Track")
        st.dataframe(track_rows, use_container_width=True, hide_index=True)


def render_datasets_tab(
    datasets: list[dict[str, Any]],
    practice_cards: list[dict[str, Any]],
) -> None:
    st.markdown("### 📊 Datasets")
    st.markdown("CSV-файлы из папки `datasets/` рядом с приложением. Предпросмотр читает только первые строки.")

    return_card_id = st.session_state.get("dataset_return_card")
    if return_card_id and any(card["id"] == return_card_id for card in practice_cards):
        st.button(
            "← К карточке практики",
            key="dataset_back_to_practice",
            on_click=open_practice_card,
            args=(return_card_id,),
            use_container_width=True,
        )

    if st.button("Пересканировать datasets/", key="rescan_datasets", use_container_width=True):
        scan_datasets.clear()
        st.rerun()

    if not DATASETS_DIR.exists() or not DATASETS_DIR.is_dir():
        st.info("Папка datasets/ пока не создана. Добавьте CSV-файлы рядом с приложением.")
        return

    if not datasets:
        st.info("CSV-файлы в datasets/ не найдены.")
        return

    summary_rows = [
        {
            "name": dataset["name"],
            "size": dataset["size"],
            "rows": dataset["rows"] if dataset["rows"] is not None else "—",
            "columns": dataset["columns"] if dataset["columns"] is not None else "—",
            "status": "ok" if not dataset.get("error") else "error",
        }
        for dataset in datasets
    ]
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    names = [dataset["name"] for dataset in datasets]
    selected_name = st.session_state.get("selected_dataset")
    if selected_name not in names:
        selected_name = names[0]
        st.session_state["selected_dataset"] = selected_name

    selected_name = st.selectbox(
        "Датасет",
        names,
        index=names.index(selected_name),
        key="selected_dataset",
    )
    selected = find_dataset_record(selected_name, datasets)
    if not selected:
        st.info("Выберите датасет.")
        return

    if selected.get("error"):
        st.warning(f"Не удалось прочитать CSV: {selected['error']}")
        return

    preview_data = read_dataset_preview(selected["path"], nrows=50)
    if preview_data["error"]:
        st.warning(f"Не удалось открыть предпросмотр: {preview_data['error']}")
        return

    st.markdown(f"#### {selected['name']}")
    meta_cols = st.columns(3)
    meta_cols[0].metric("Размер", selected["size"])
    meta_cols[1].metric("Строк", selected["rows"] if selected["rows"] is not None else "—")
    meta_cols[2].metric("Колонок", selected["columns"] if selected["columns"] is not None else "—")

    st.markdown("#### Preview: первые 50 строк")
    st.dataframe(preview_data["preview"], use_container_width=True)

    st.markdown("#### Колонки и типы")
    st.dataframe(preview_data["dtypes"], use_container_width=True, hide_index=True)

    st.markdown("#### Describe: числовые колонки")
    if preview_data["describe"] is None:
        st.info("Числовых колонок в первых строках не найдено.")
    else:
        st.dataframe(preview_data["describe"], use_container_width=True)


def render_scratch_tab(datasets: list[dict[str, Any]]) -> None:
    st.markdown("### ⚡ Scratch")
    st.markdown(
        "Лёгкий текстовый раннер: код выполняется отдельным Python-процессом, без живого состояния и без рендера графиков."
    )

    if "scratch_code" not in st.session_state:
        st.session_state["scratch_code"] = default_scratch_code(datasets)

    timeout_seconds = st.number_input(
        "Timeout, сек",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
        key="scratch_timeout",
    )

    if st_ace is not None:
        code = st_ace(
            value=st.session_state["scratch_code"],
            language="python",
            theme="tomorrow_night",
            height=360,
            key="scratch_ace",
        )
        if code is not None:
            st.session_state["scratch_code"] = code
    else:
        st.info("streamlit-ace не установлен, поэтому открыт простой текстовый редактор.")
        st.text_area("Python code", height=360, key="scratch_code")

    if st.button("▶ Запустить", key="run_scratch", use_container_width=True):
        result = run_scratch_code(st.session_state["scratch_code"], int(timeout_seconds))
        if result["timed_out"]:
            st.warning(f"⏱ таймаут после {timeout_seconds} сек")
        else:
            st.caption(f"exit code: {result['exit_code']} · time: {result['elapsed']:.2f}s")

        st.markdown("#### stdout")
        st.code(result["stdout"] or "", language="text")
        st.markdown("#### stderr")
        st.code(result["stderr"] or "", language="text")


def render_notebook_cell(
    cell: dict[str, str],
    index: int,
    kernel_state: dict[str, Any],
) -> None:
    cell_id = cell["id"]
    code_key = f"notebook_code_{cell_id}"
    editor_key = f"notebook_editor_{cell_id}"
    st.session_state.setdefault(code_key, "")
    outputs = st.session_state.setdefault("notebook_outputs", {}).get(cell_id, [])
    is_busy = kernel_state.get("status") == "busy"
    is_this_running = is_busy and kernel_state.get("busy_cell_id") == cell_id

    st.markdown(
        f"""
<div class="learning-panel">
    <div class="learning-panel-title">Ячейка {index}</div>
    <div class="muted-small">Код выполняется в живом Python-ядре, состояние сохраняется между ячейками.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    use_plain_editor = st.session_state.get("notebook_plain_editor", False) or st_ace is None
    if not use_plain_editor:
        code = st_ace(
            value=st.session_state[code_key],
            language="python",
            theme="tomorrow_night",
            height=180,
            key=editor_key,
        )
        if code is not None:
            st.session_state[code_key] = code
    else:
        if st_ace is None:
            st.info("streamlit-ace не установлен, поэтому открыт простой текстовый редактор.")
        st.text_area(f"Код ячейки {index}", height=180, key=code_key)

    cols = st.columns([0.55, 0.25, 0.20])
    run_clicked = cols[0].button(
        "▶ Запустить ячейку",
        key=f"notebook_run_{cell_id}",
        disabled=is_busy or kernel_state.get("status") == "dead",
        use_container_width=True,
    )
    if run_clicked:
        start_notebook_cell(cell_id, st.session_state.get(code_key, ""))
        st.rerun()
    cols[1].button(
        "Обновить вывод",
        key=f"notebook_refresh_{cell_id}",
        use_container_width=True,
    )
    cols[2].button(
        "Удалить",
        key=f"notebook_delete_{cell_id}",
        on_click=delete_notebook_cell,
        args=(cell_id,),
        disabled=is_busy or len(st.session_state.get("notebook_cells", [])) <= 1,
        use_container_width=True,
    )

    if is_this_running:
        with st.spinner("Ячейка выполняется в Python-ядре..."):
            st.caption("UI живой: можно прервать ядро сверху или нажать «Обновить вывод».")

    st.markdown("##### Output")
    if outputs:
        for output in outputs:
            render_notebook_output(output)
    else:
        st.caption("Пока нет вывода.")


def render_notebook_tab() -> None:
    st.markdown("### 📓 Notebook")
    st.markdown(
        "Живое Python-ядро для экспериментов: переменные, импорты, датафреймы и модели сохраняются между ячейками."
    )

    init_notebook_state()
    kernel_state = refresh_notebook_kernel_state()
    poll_notebook_execution(kernel_state, time_budget=0.8)
    kernel_state = refresh_notebook_kernel_state()
    status = str(kernel_state.get("status") or "dead")
    status_label = {
        "idle": "idle",
        "busy": "busy",
        "dead": "dead",
    }.get(status, status)
    status_class = {
        "idle": "status-done",
        "busy": "status-reading",
        "dead": "status-repeat",
    }.get(status, "status-not-started")

    st.markdown(
        f"""
<div class="frontmatter-row">
    <span class="status-pill {status_class}">kernel: {html.escape(status_label)}</span>
    <span class="fm-chip">cwd: {html.escape(str(PROJECT_ROOT))}</span>
</div>
        """,
        unsafe_allow_html=True,
    )

    if kernel_state.get("last_error"):
        st.warning(kernel_state["last_error"])

    if KernelManager is None:
        st.error("Notebook требует jupyter_client и ipykernel. Установите зависимости из requirements.txt.")
        return

    controls = st.columns(4)
    controls[0].button(
        "➕ Добавить ячейку",
        key="notebook_add_cell",
        on_click=add_notebook_cell,
        disabled=status == "busy",
        use_container_width=True,
    )
    controls[1].button(
        "⏹ Прервать",
        key="notebook_interrupt",
        on_click=interrupt_notebook_kernel,
        disabled=status != "busy",
        use_container_width=True,
    )
    controls[2].button(
        "🔄 Перезапустить ядро",
        key="notebook_restart",
        on_click=restart_notebook_kernel,
        use_container_width=True,
    )
    controls[3].button(
        "Обновить",
        key="notebook_refresh_all",
        use_container_width=True,
    )
    st.checkbox(
        "Простой редактор без iframe",
        key="notebook_plain_editor",
        help="Полезно для доступности, отладки и случаев, когда Ace-редактор ведет себя нестабильно.",
    )

    if status == "dead":
        st.info("Ядро остановлено. Нажмите «Перезапустить ядро», чтобы продолжить.")
        return

    for index, cell in enumerate(st.session_state["notebook_cells"], start=1):
        render_notebook_cell(cell, index, kernel_state)


def render_progress(
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    algorithm_lessons: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
) -> None:
    notes = all_notes(sections)
    total = len(notes)
    done = sum(1 for note in notes if get_note_status(note) == STATUS_DONE)
    reading = sum(1 for note in notes if get_note_status(note) == STATUS_READING)
    repeat = sum(1 for note in notes if get_note_status(note) == STATUS_REPEAT)
    not_started = total - done - reading - repeat
    ratio = completion_ratio(notes)

    st.markdown("### Progress")
    st.markdown("Здесь видно, превращается ли база в реальный учебный путь.")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Готово", done)
    metric_cols[1].metric("Читаю", reading)
    metric_cols[2].metric("Повторить", repeat)
    metric_cols[3].metric("Не начато", not_started)

    st.progress(ratio)
    st.caption(f"Общий прогресс: {done}/{total} заметок ({ratio:.0%})")

    practice_stats = practice_progress(practice_cards)
    st.markdown("#### Практика")
    practice_total = practice_stats["total"]
    practice_done = practice_stats[PRACTICE_DONE]
    practice_ratio = practice_done / practice_total if practice_total else 0.0
    practice_cols = st.columns(3)
    practice_cols[0].metric("Карточек", practice_total)
    practice_cols[1].metric("В работе", practice_stats[PRACTICE_DOING])
    practice_cols[2].metric("Сделано", practice_done)
    st.progress(practice_ratio)
    st.caption(f"Практика: {practice_done}/{practice_total} карточек ({practice_ratio:.0%})")

    mentor_stats = mentor_tasks_progress(mentor_tasks)
    mentor_total = mentor_stats["total"]
    mentor_done = mentor_stats["done"]
    mentor_ratio = mentor_done / mentor_total if mentor_total else 0.0
    st.markdown("#### Mentor tasks")
    mentor_cols = st.columns(2)
    mentor_cols[0].metric("Автозадач", mentor_total)
    mentor_cols[1].metric("Решено", mentor_done)
    st.progress(mentor_ratio)
    st.caption(f"Задачи ментора: {mentor_done}/{mentor_total} ({mentor_ratio:.0%})")

    algorithm_stats = algorithm_progress(algorithm_lessons)
    algorithm_total = algorithm_stats["total"]
    algorithm_done = algorithm_stats["done"]
    algorithm_ratio = algorithm_done / algorithm_total if algorithm_total else 0.0
    st.markdown("#### Algorithms Lab")
    algorithm_cols = st.columns(2)
    algorithm_cols[0].metric("Уроков", algorithm_total)
    algorithm_cols[1].metric("Пройдено", algorithm_done)
    st.progress(algorithm_ratio)
    st.caption(f"Алгоритмы: {algorithm_done}/{algorithm_total} уроков ({algorithm_ratio:.0%})")

    output_stats = portfolio_progress(practice_cards)
    output_total = output_stats["total"]
    output_done = output_stats["with_outputs"]
    output_ratio = output_done / output_total if output_total else 0.0
    st.markdown("#### Portfolio outputs")
    output_cols = st.columns(2)
    output_cols[0].metric("Output записан", output_done)
    output_cols[1].metric("Без output", output_stats["missing"])
    st.progress(output_ratio)
    st.caption(f"Портфолио-след: {output_done}/{output_total} карточек ({output_ratio:.0%})")

    next_note = find_next_note(sections)
    if next_note:
        section_label = humanize_section_name(next_note["section_key"])
        st.markdown(
            f"""
<div class="learning-panel">
    <div class="learning-panel-title">Что открыть дальше</div>
    <div class="muted-small">{html.escape(section_label)} / {html.escape(next_note["display_name"])}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Перейти к следующей заметке",
            key="progress_open_next",
            on_click=open_note_from_roadmap,
            args=(next_note,),
            use_container_width=True,
        )

    st.markdown("#### По разделам")
    for section_key, section_notes in sections.items():
        stats = section_progress(section_notes)
        total_section = stats["total"]
        ratio_section = stats[STATUS_DONE] / total_section if total_section else 0.0
        st.markdown(
            f"""
<div class="section-progress-row">
    <strong>{html.escape(humanize_section_name(section_key))}</strong>
    <div class="muted-small">
        {stats[STATUS_DONE]}/{total_section} готово ·
        {stats[STATUS_READING]} читаю ·
        {stats[STATUS_REPEAT]} повторить
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(ratio_section)


def open_source_note(note: dict[str, str]) -> None:
    set_active_note(note, push_history=False)
    st.session_state["active_tab"] = "Theory"


def render_problem_link(record: dict[str, Any], index: int, prefix: str) -> None:
    source_note = record["source_note"]
    target = str(record.get("target") or "")
    reason = str(record.get("reason") or "")
    label = str(record.get("label") or target)
    st.markdown(
        f"""
<div class="health-row">
    <div class="link-label">{html.escape(label)}</div>
    <div class="link-path">target: {html.escape(target)}</div>
    <div class="link-path">источник: {html.escape(link_path_label(source_note))}</div>
    <div class="link-path">причина: {html.escape(reason)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        "Открыть источник",
        key=f"{prefix}_open_source_{index}_{source_note['path']}_{target}",
        on_click=open_source_note,
        args=(source_note,),
        use_container_width=True,
    )


def render_links_health(graph: dict[str, Any]) -> None:
    st.markdown("### 🔗 Links Health")
    st.markdown("Аудит всех Obsidian-ссылок в vault. Это карта надежности твоей базы.")

    if st.button("Пересканировать ссылки", key="rescan_links", use_container_width=True):
        scan_link_graph.clear()
        st.rerun()

    summary = graph["summary"]
    cols = st.columns(4)
    cols[0].metric("Всего ссылок", summary["total"])
    cols[1].metric("Резолвится", summary["resolved"])
    cols[2].metric("Битые", summary["broken"])
    cols[3].metric("Неоднозначные", summary["ambiguous"])

    if summary["broken"] == 0 and summary["ambiguous"] == 0:
        st.success("Все ссылки на месте ✅")
        return

    broken = graph["broken"]
    ambiguous = graph["ambiguous"]

    if broken:
        st.markdown("#### Битые ссылки")
        for index, record in enumerate(broken):
            render_problem_link(record, index, "broken")
    else:
        st.info("Битых ссылок нет.")

    if ambiguous:
        st.markdown("#### Неоднозначные ссылки")
        st.caption("Приложение выбирает ближайшую заметку по дереву, но лучше уточнить путь в Obsidian-ссылке.")
        for index, record in enumerate(ambiguous):
            render_problem_link(record, index, "ambiguous")
    else:
        st.info("Неоднозначных ссылок нет.")


def render_help() -> None:
    with st.expander("Пример тестового vault"):
        st.markdown(
            """
Создайте такую структуру и укажите путь к `test_vault` в сайдбаре:

```text
test_vault/
├── welcome.md
├── ai/
│   └── prompts.md
├── data_science/
│   └── pandas/
│       └── groupby.md
└── .obsidian/
    └── workspace.json
```

`welcome.md`

```markdown
---
title: Welcome
tags: [intro, sandbox]
---

# Добро пожаловать

Это корневая заметка. Она должна попасть в раздел «Без раздела».
```

`ai/prompts.md`

```markdown
---
title: Prompt Engineering
tags:
  - ai
  - prompts
---

# Prompt Engineering

Связь с другой заметкой: [[Welcome]]

Главная идея: инструкции должны быть ясными и проверяемыми.
```

`data_science/pandas/groupby.md`

```markdown
---
title: Pandas GroupBy
tags: [python, pandas]
level: beginner
---

# GroupBy

`groupby` нужен для группировки и агрегации данных.
```
            """
        )


def main() -> None:
    inject_styles()
    st.title(APP_TITLE)

    env_vault_path = os.environ.get("VAULT_PATH", "").strip()
    if "vault_path" not in st.session_state:
        st.session_state["vault_path"] = env_vault_path
    st.session_state.setdefault("note_history", [])

    vault_path = st.session_state.get("vault_path", "").strip()
    if not vault_path:
        st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
        st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
        st.info("Укажите путь к Obsidian vault")
        render_help()
        return

    vault = Path(vault_path).expanduser()
    if not vault.exists() or not vault.is_dir():
        st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
        st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
        st.error(f"Путь не существует или не является папкой: {vault_path}")
        render_help()
        return

    resolved_vault = vault.resolve()
    sections = scan_vault(str(resolved_vault))
    if not sections:
        st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
        st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
        st.info("Markdown-файлы не найдены")
        render_help()
        return

    note_index = build_note_index(sections)
    graph = scan_link_graph(str(resolved_vault))
    practice_cards, practice_warnings = scan_practice_cards()
    datasets = scan_datasets(DATASETS_DIR)
    algorithm_lessons = scan_algorithm_lessons()
    interview_data = load_interview_questions()
    architecture_data = load_architecture_guidelines()
    mentor_data = load_mentor_tasks(MENTOR_TASKS_PATH)
    tab_options = [
        "Home",
        "Theory",
        "🎯 Practice",
        "🎯 Tasks",
        "📁 Portfolio",
        "📊 Datasets",
        "⚡ Scratch",
        "📓 Notebook",
        "🧩 Algorithms",
        "🎤 Interviews",
        "🏗 Architecture",
        "🧭 Theory Quality",
        "Roadmap",
        "Progress",
        "🔗 Links Health",
    ]
    if st.session_state.get("active_tab") not in tab_options:
        st.session_state["active_tab"] = "Home"
    selected_section, selected_note = render_sidebar(sections)

    active_tab = st.radio(
        "Режим",
        tab_options,
        key="active_tab",
        horizontal=True,
        label_visibility="collapsed",
    )

    if active_tab == "Home":
        render_dashboard(sections, practice_cards, datasets, graph)
    elif active_tab == "Theory":
        if selected_note is None:
            st.info("Выберите заметку в сайдбаре.")
            return
        render_note(selected_section, selected_note, resolved_vault, note_index, graph, sections, practice_cards)
    elif active_tab == "🎯 Practice":
        render_practice_tab(practice_cards, practice_warnings, note_index, datasets)
    elif active_tab == "🎯 Tasks":
        render_tasks_tab(mentor_data)
    elif active_tab == "📁 Portfolio":
        render_portfolio_tab(practice_cards)
    elif active_tab == "📊 Datasets":
        render_datasets_tab(datasets, practice_cards)
    elif active_tab == "⚡ Scratch":
        render_scratch_tab(datasets)
    elif active_tab == "📓 Notebook":
        render_notebook_tab()
    elif active_tab == "🧩 Algorithms":
        render_algorithms_tab(algorithm_lessons)
    elif active_tab == "🎤 Interviews":
        render_interviews_tab(interview_data)
    elif active_tab == "🏗 Architecture":
        render_architecture_tab(architecture_data)
    elif active_tab == "🧭 Theory Quality":
        render_theory_quality_tab(note_index)
    elif active_tab == "Roadmap":
        render_roadmap(sections)
    elif active_tab == "Progress":
        render_progress(sections, practice_cards, algorithm_lessons, mentor_data.get("tasks", []))
    else:
        render_links_health(graph)


if __name__ == "__main__":
    main()
