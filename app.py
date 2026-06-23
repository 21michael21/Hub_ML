from __future__ import annotations

import ast
import hashlib
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
from core.experiments.tracker import (
    SUPPORTED_METRICS,
    compare_experiments,
    experiment_records_path,
    load_experiment_records,
    save_experiment_record,
    summarize_experiments,
)
from core.interview_arena import (
    PRACTICE_MODES,
    extract_expected_complexity,
    infer_difficulty,
    normalize_algorithm_attempt,
    normalize_interview_answer_attempt,
    summarize_interview_arena_progress,
)
from core.portfolio.exporter import EXPORT_WARNING, generate_portfolio_markdown, portfolio_export_path
from core.projects.loader import load_project_recipes_from_dirs
from core.projects.models import calculate_readiness, checklist_progress
from core.projects.progress import (
    completed_milestone_ids,
    is_project_complete,
    milestone_record,
    project_progress_from_record,
    set_checklist_item,
    set_milestone_completion,
    set_milestone_data,
    set_project_completion,
    set_project_completion_if_ready,
)
from core.projects.workspace import create_project_workspace, project_workspace_path
from core.reports.theory_quality import (
    coverage_by_track,
    coverage_summary,
    load_json_report,
    missing_required_topics,
    report_list,
    theory_summary,
    weakest_notes,
)
from core.search import SearchIndex, SearchItem, build_search_index, search as semantic_search
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
PORTFOLIO_DIR = PROJECT_ROOT / "portfolio"
USER_PROJECTS_DIR = PROJECT_ROOT / "user_projects"
ALGORITHMS_DIR = PROJECT_ROOT / "content" / "source" / "vkat" / "VKAT-main" / "algos_patterns"
INTERVIEW_QUESTIONS_PATH = PROJECT_ROOT / "content" / "interview_questions" / "ml_ds_interview_questions.json"
ARCHITECTURE_GUIDELINES_PATH = PROJECT_ROOT / "content" / "study" / "architecture_guidelines.html"
ARCHITECTURE_GUIDELINES_INDEX_PATH = PROJECT_ROOT / "content" / "study" / "architecture_guidelines_index.json"
MENTOR_TASKS_PATH = PROJECT_ROOT / "content" / "extracted" / "mentor_tasks.json"
THEORY_AUDIT_REPORT_PATH = PROJECT_ROOT / "content" / "reports" / "theory_audit.json"
COVERAGE_REPORT_PATH = PROJECT_ROOT / "content" / "reports" / "coverage_report.json"
CONTENT_GATE_REPORT_PATH = PROJECT_ROOT / "content" / "reports" / "content_gate_report.json"
DATA_LAB_PROJECTS_DIR = PROJECT_ROOT / "content" / "projects" / "data_lab"
ML_LAB_PROJECTS_DIR = PROJECT_ROOT / "content" / "projects" / "ml_lab"
PROJECT_RECIPE_DIRS = (DATA_LAB_PROJECTS_DIR, ML_LAB_PROJECTS_DIR)
SEMANTIC_SEARCH_INDEX_KEY = "semantic_search_index"
SEMANTIC_SEARCH_META_KEY = "semantic_search_meta"
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
NAV_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("Home", [("Home", "Home", "◧")]),
    (
        "Learn",
        [
            ("Theory", "Theory", "◎"),
            ("🎯 Practice", "Practice", "✎"),
            ("🧭 Theory Quality", "Theory Quality", "◇"),
            ("Roadmap", "Roadmap", "▤"),
            ("Progress", "Progress", "▥"),
        ],
    ),
    (
        "Build",
        [
            ("🧪 Data Lab Projects", "Data Lab", "▣"),
            ("🤖 ML Lab", "ML Lab", "▧"),
            ("📓 Notebook", "Notebook", "▦"),
            ("📊 Datasets", "Datasets", "▨"),
            ("⚡ Scratch", "Scratch", "⌁"),
        ],
    ),
    (
        "Train",
        [
            ("🎯 Tasks", "Tasks", "✓"),
            ("🧩 Algorithms", "Algorithms", "⌘"),
            ("🎤 Interviews", "Interviews", "?"),
        ],
    ),
    (
        "Output",
        [
            ("📁 Portfolio", "Portfolio", "□"),
            ("🧪 Experiments", "Experiments", "◌"),
            ("🏗 Architecture", "Architecture", "△"),
            ("🔗 Links Health", "Links Health", "↔"),
        ],
    ),
]
NAV_LABELS = {tab: label for _, items in NAV_GROUPS for tab, label, _ in items}
NAV_ICONS = {tab: icon for _, items in NAV_GROUPS for tab, _, icon in items}
NAV_GROUP_BY_TAB = {tab: group for group, items in NAV_GROUPS for tab, _, _ in items}
TAB_OPTIONS = list(NAV_LABELS)


st.set_page_config(page_title=APP_TITLE, page_icon="📚", layout="wide")


def inject_styles() -> None:
    st.markdown(
        """<style>
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap");
    :root {
        --bg:#0A0C11; --surface:#12151D; --surface-2:#1A1F29; --raised:#232A36;
        --border:#313A48; --border-soft:#232A36; --border-strong:#3D4757;
        --text:#F1F3F8; --dim:#AAB3C2; --faint:#6A7382;
        --accent:#8B9BFF; --accent-2:#6B7BF0; --accent-soft:rgba(139,155,255,.16);
        --pass:#4FD06A; --warn:#E5B23A; --fail:#FF5E54; --info:#5FAEFF;
        --r:13px; --r-sm:8px; --s1:8px; --s2:14px; --s3:22px; --s4:32px;
        --f-display:"Space Grotesk"; --f-ui:"IBM Plex Sans"; --f-mono:"IBM Plex Mono";
        --ease:cubic-bezier(.2,.7,.3,1);
        --radius: var(--r);
        --radius-sm: var(--r-sm);
        --font-display: var(--f-display), sans-serif;
        --font-body: var(--f-ui), sans-serif;
        --font-mono: var(--f-mono), monospace;

        --ls-muted: var(--dim);
        --ls-border: var(--border);
        --ls-soft: var(--surface-2);
        --ls-softer: var(--surface);
        --ls-link: var(--info);
        --ls-link-bg: rgba(95,174,255,0.14);
        --ls-chip-bg: var(--surface-2);
        --ls-code-bg: var(--raised);
        --ls-quote-bg: var(--surface-2);
    }

    @keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
    @keyframes shimmer{0%{background-position:-360px 0}100%{background-position:360px 0}}
    @keyframes growBar{from{width:0}}
    @keyframes spin{to{transform:rotate(360deg)}}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
    @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background:
            radial-gradient(rgba(139,155,255,0.055) 1px, transparent 1px),
            var(--bg);
        background-size: 26px 26px, auto;
        color: var(--text);
        font-family: var(--f-ui);
        font-size: 15px;
        line-height: 1.55;
        -webkit-font-smoothing: antialiased;
    }

    * {
        box-sizing: border-box;
    }

    :focus-visible {
        outline: 2px solid var(--accent);
        outline-offset: 2px;
        border-radius: 6px;
    }

    .mono,
    .chip,
    .status-chip,
    .metric-tile-value,
    .metric-tile-meta,
    .section-eyebrow,
    code,
    pre {
        font-family: var(--f-mono);
    }

    h1, h2, h3, h4,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4 {
        color: var(--text);
        font-family: var(--f-display);
        letter-spacing: 0;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F121A 0%, var(--bg) 100%);
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        justify-content: flex-start;
        border: 1px solid transparent;
        border-radius: var(--radius-sm);
        background: transparent;
        color: var(--dim);
        font-family: var(--f-ui);
        font-size: 0.86rem;
        padding: 0.38rem 0.62rem;
        text-align: left;
        transition: background 0.14s var(--ease), color 0.14s var(--ease), border-color 0.14s var(--ease), transform 0.14s var(--ease);
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: var(--border);
        background: var(--surface);
        color: var(--text);
        transform: translateX(2px);
    }

    [data-testid="stSidebar"] .stButton > button:focus-visible {
        outline: 2px solid var(--accent);
        outline-offset: 2px;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stToolbar"] {
        color: var(--dim);
    }

    .main .block-container {
        max-width: 980px;
        padding: var(--s4) var(--s4) 5rem var(--s4);
    }

    .content-container {
        max-width: 980px;
        margin-left: auto;
        margin-right: auto;
    }

    .section-gap {
        margin-top: var(--s4);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        margin-top: 0;
    }

    .sidebar-logo {
        color: var(--text);
        font-family: var(--f-display);
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0;
        padding: 0.15rem 0 0.35rem;
    }

    .nav-group-label {
        margin: 1rem 0 0.32rem;
        color: var(--faint);
        font-family: var(--f-mono);
        font-size: 0.66rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .nav-active-row {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        margin: 0.14rem 0 0.24rem;
        border: 1px solid rgba(139,155,255,0.22);
        border-left: 3px solid var(--accent);
        border-radius: var(--radius-sm);
        background: var(--accent-soft);
        color: var(--text);
        font-size: 0.86rem;
        font-weight: 600;
        padding: 0.42rem 0.6rem;
    }

    .nav-active-row .nav-ico {
        color: var(--accent);
        font-family: var(--f-mono);
    }

    .ide-topbar,
    .breadcrumb-shell {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--s2);
        min-height: 42px;
        margin: 0 0 var(--s3);
        border: 1px solid var(--border-soft);
        border-radius: var(--r-sm);
        background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0)), var(--surface);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035);
        padding: 0.55rem 0.72rem;
        color: var(--faint);
        font-family: var(--f-mono);
        font-size: 0.74rem;
        letter-spacing: 0.03em;
    }

    .ide-topbar-left,
    .ide-topbar-right {
        display: inline-flex;
        align-items: center;
        min-width: 0;
    }

    .ide-topbar-left {
        gap: 0.45rem;
    }

    .ide-topbar-right {
        flex: 0 0 auto;
        border: 1px solid var(--border);
        border-radius: 999px;
        background: var(--raised);
        color: var(--dim);
        padding: 0.22rem 0.58rem;
    }

    .ide-topbar strong,
    .breadcrumb-shell strong {
        color: var(--faint);
        font-weight: 500;
    }

    .ide-topbar .sep {
        color: var(--faint);
    }

    .ide-topbar .ctx {
        color: var(--dim);
    }

    .ide-statusbar {
        position: sticky;
        bottom: 0;
        z-index: 20;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--s2);
        margin-top: var(--s4);
        border: 1px solid var(--border-soft);
        border-radius: var(--r-sm);
        background: rgba(18,21,29,0.96);
        color: var(--dim);
        font-family: var(--f-mono);
        font-size: 0.72rem;
        letter-spacing: 0.02em;
        padding: 0.46rem 0.66rem;
        backdrop-filter: blur(14px);
        box-shadow: 0 -10px 26px rgba(0,0,0,0.24);
    }

    .ide-statusbar-left,
    .ide-statusbar-right {
        display: flex;
        align-items: center;
        gap: 0.62rem;
        min-width: 0;
    }

    .ide-statusbar-left {
        flex-wrap: wrap;
    }

    .ide-statusbar-right {
        margin-left: auto;
        color: var(--faint);
        text-align: right;
    }

    .ide-statusbar-item {
        display: inline-flex;
        align-items: center;
        gap: 0.32rem;
        white-space: nowrap;
    }

    .ide-statusbar-dot {
        width: 0.42rem;
        height: 0.42rem;
        border-radius: 999px;
        background: var(--faint);
        box-shadow: 0 0 0 3px rgba(106,115,130,0.12);
    }

    .ide-statusbar-dot.busy {
        background: var(--warn);
        box-shadow: 0 0 0 3px rgba(229,178,58,0.16);
        animation: pulse 1.2s var(--ease) infinite;
    }

    .ide-statusbar-dot.idle {
        background: var(--pass);
        box-shadow: 0 0 0 3px rgba(79,208,106,0.14);
    }

    .ide-statusbar-dot.dead,
    .ide-statusbar-dot.error {
        background: var(--fail);
        box-shadow: 0 0 0 3px rgba(255,94,84,0.14);
    }

    @media (max-width: 760px) {
        .ide-topbar,
        .ide-statusbar {
            align-items: flex-start;
            flex-direction: column;
        }

        .ide-topbar-right,
        .ide-statusbar-right {
            margin-left: 0;
        }
    }

    .note-header {
        max-width: 980px;
        margin: 0 auto var(--s3) auto;
        border: 1px solid var(--border);
        border-radius: var(--r);
        background: var(--surface);
        padding: var(--s3);
        animation: fadeUp .32s var(--ease) both;
    }

    .breadcrumbs {
        color: var(--ls-muted);
        font-family: var(--f-mono);
        font-size: 0.84rem;
        line-height: 1.45;
        margin-bottom: 0.55rem;
    }

    .note-header-title {
        color: var(--text);
        font-family: var(--f-display);
        font-size: clamp(1.35rem, 2.8vw, 2.25rem);
        font-weight: 700;
        letter-spacing: 0;
        line-height: 1.08;
        margin: 0 0 var(--s2);
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
        background: var(--surface-2);
        color: var(--text);
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
        color: var(--text);
        font-size: 0.9em;
    }

    div[data-testid="stMarkdownContainer"] pre {
        border: 1px solid var(--ls-border);
        border-radius: var(--radius-sm);
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
        max-width: 980px;
        margin: var(--s4) auto var(--s2) auto;
        animation: fadeUp .32s var(--ease) both;
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
        max-width: 980px;
        margin: 0 auto var(--s3) auto;
        padding: var(--s3);
        border: 1px solid var(--border);
        border-radius: var(--r);
        background: var(--surface);
        animation: fadeUp .32s var(--ease) both;
    }

    .learning-panel-title {
        margin-bottom: 0.45rem;
        font-weight: 720;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.32rem;
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.18rem 0.62rem;
        font-family: var(--font-mono);
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.04em;
        line-height: 1.5;
        background: var(--surface-2);
    }

    .status-reading {
        color: var(--warn);
        background: rgba(216,165,55,0.10);
        border-color: rgba(216,165,55,0.30);
    }

    .status-done {
        color: var(--pass);
        background: rgba(70,194,101,0.10);
        border-color: rgba(70,194,101,0.30);
    }

    .status-repeat {
        color: var(--fail);
        background: rgba(240,88,79,0.10);
        border-color: rgba(240,88,79,0.30);
    }

    .status-not-started {
        color: var(--faint);
    }

    .roadmap-card {
        padding: 0.85rem 1rem;
        border: 1px solid var(--border);
        border-radius: var(--r);
        background: var(--surface);
        margin-bottom: 0.75rem;
        animation: fadeUp .32s var(--ease) both;
        transition: border-color .16s var(--ease), transform .16s var(--ease);
    }

    .roadmap-card:hover {
        border-color: var(--border-strong);
        transform: translateY(-2px);
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
        border: 1px solid var(--border);
        border-radius: var(--r-sm);
        background: var(--surface);
        margin: var(--s2) 0;
        padding: 0.72rem 0.9rem;
        border-bottom: 1px solid var(--border-soft);
        animation: fadeUp .32s var(--ease) both;
    }

    .section-progress-row:last-child {
        border-bottom: 0;
    }

    .link-card {
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        background: var(--surface);
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
        border: 1px solid var(--border);
        border-radius: var(--r-sm);
        padding: 0.75rem 0.9rem;
        background: var(--surface);
        margin: 0.55rem 0;
        animation: fadeUp .32s var(--ease) both;
        transition: background .16s var(--ease), border-color .16s var(--ease);
    }

    .health-row:hover {
        border-color: var(--border-strong);
        background: var(--surface-2);
    }

    .health-row-pass {
        border-color: rgba(79,208,106,0.28);
        background: rgba(79,208,106,0.06);
    }

    .health-row-fail,
    .health-row-error {
        border-color: rgba(255,94,84,0.28);
        background: rgba(255,94,84,0.06);
    }

    .today-hero {
        max-width: 780px;
        margin: 0 auto 1rem auto;
        padding: 1rem 1.1rem;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        background: linear-gradient(135deg, var(--accent-soft), rgba(70,194,101,0.08));
    }

    .today-title {
        font-size: 1.05rem;
        font-weight: 760;
        margin-bottom: 0.25rem;
    }

    .today-card {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 0.85rem 1rem;
        background: var(--surface);
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
        border: 1px solid var(--border);
        border-radius: var(--radius);
        background: var(--surface);
    }

    .practice-title {
        font-weight: 760;
        margin-bottom: 0.35rem;
    }

    .practice-output {
        border-left: 3px solid var(--pass);
        padding: 0.45rem 0.8rem;
        margin: 0.75rem 0;
        background: rgba(79,208,106,0.08);
        color: var(--text);
    }

    .practice-checklist {
        margin: 0.55rem 0 0 0;
        padding-left: 1.15rem;
    }

    .practice-checklist li {
        margin: 0.28rem 0;
        color: var(--text);
    }

    .eyebrow,
    .section-eyebrow {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: var(--s3) 0 var(--s2);
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 10.5px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }

    .eyebrow::after,
    .section-eyebrow::after {
        content: "";
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    .console-card {
        border: 1px solid var(--border);
        border-radius: var(--r);
        background: var(--surface);
        padding: 16px 18px;
        box-shadow: 0 18px 50px rgba(0,0,0,0.20);
        animation: fadeUp .4s var(--ease) both;
        transition: border-color .16s var(--ease), transform .16s var(--ease), box-shadow .16s var(--ease);
    }

    .console-card:hover {
        border-color: var(--border-strong);
        transform: translateY(-2px);
        box-shadow: 0 22px 58px rgba(0,0,0,0.24);
    }

    .console-card-eyebrow {
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 0.66rem;
        letter-spacing: 0.11em;
        text-transform: uppercase;
    }

    .console-card-title {
        margin-top: 0.4rem;
        color: var(--text);
        font-family: var(--font-display);
        font-size: 1rem;
        font-weight: 600;
        line-height: 1.25;
    }

    .console-card-body {
        margin-top: 0.45rem;
        color: var(--dim);
        font-size: 0.9rem;
        line-height: 1.55;
    }

    .console-card-meta {
        margin-top: 0.65rem;
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 0.72rem;
    }

    .console-panel {
        overflow: hidden;
        border: 1px solid var(--border);
        border-radius: var(--r);
        background: var(--surface);
        animation: fadeUp .4s var(--ease) both;
    }

    .console-panel .phead {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 11px 16px;
        border-bottom: 1px solid var(--border);
        background: var(--surface-2);
    }

    .dot3 {
        display: inline-flex;
        gap: 6px;
        margin-right: 4px;
    }

    .dot3 i,
    .dot3 span {
        width: 9px;
        height: 9px;
        border-radius: 999px;
    }

    .dot3 i:nth-child(1),
    .dot3 span:nth-child(1) {
        background: var(--fail);
    }

    .dot3 i:nth-child(2),
    .dot3 span:nth-child(2) {
        background: var(--warn);
    }

    .dot3 i:nth-child(3),
    .dot3 span:nth-child(3) {
        background: var(--pass);
    }

    .console-panel .editor,
    .editor-wrapper {
        overflow: auto;
        padding: 16px;
        background: #0D1016;
        color: #cfd6e4;
        font-family: var(--font-mono);
        font-size: 12.5px;
        line-height: 1.7;
        white-space: pre;
    }

    .metric-tile {
        border: 1px solid var(--border);
        border-radius: var(--r);
        background: var(--surface);
        padding: 16px 18px;
        animation: fadeUp .4s var(--ease) both;
        transition: border-color .16s var(--ease), transform .16s var(--ease);
    }

    .metric-tile:hover {
        border-color: var(--border-strong);
        transform: translateY(-2px);
    }

    .metric-tile .n,
    .metric-tile-value {
        color: var(--text);
        font-family: var(--font-mono);
        font-size: 23px;
        font-weight: 600;
        letter-spacing: -0.02em;
        line-height: 1;
    }

    .metric-tile .n small,
    .metric-tile-total {
        color: var(--faint);
        font-size: 14px;
    }

    .metric-tile-label {
        margin-top: 0.45rem;
        color: var(--dim);
        font-size: 0.82rem;
    }

    .metric-tile-meta {
        margin-top: 0.2rem;
        color: var(--faint);
        font-size: 0.68rem;
    }

    .metric-tile .bar,
    .metric-bar {
        height: 5px;
        margin-top: 11px;
        overflow: hidden;
        border-radius: 999px;
        background: var(--surface-2);
    }

    .metric-tile .bar i,
    .metric-bar-fill {
        display: block;
        height: 100%;
        border-radius: 999px;
        background: var(--accent);
        animation: growBar 1s var(--ease) both;
    }

    .metric-fill-pass,
    .metric-fill-done,
    .metric-fill-ready {
        background: var(--pass);
    }

    .metric-fill-warn,
    .metric-fill-in-progress,
    .metric-fill-weak {
        background: var(--warn);
    }

    .metric-fill-fail,
    .metric-fill-error,
    .metric-fill-blocked {
        background: var(--fail);
    }

    .metric-fill-info {
        background: var(--info);
    }

    .home-resume-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.85rem;
        margin-bottom: 1.3rem;
        animation: fadeUp .32s var(--ease) both;
    }

    .home-metric-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.85rem;
        margin-bottom: 1.3rem;
        animation: fadeUp .32s var(--ease) both;
    }

    .today-plan-row {
        display: grid;
        grid-template-columns: auto 1fr auto auto;
        align-items: center;
        gap: 0.75rem;
        border-bottom: 1px solid var(--border-soft);
        padding: 0.72rem 0;
        animation: fadeUp .32s var(--ease) both;
    }

    .today-plan-row:last-child {
        border-bottom: 0;
    }

    .type-tag {
        min-width: 4.3rem;
        border-radius: 6px;
        background: var(--accent-soft);
        color: var(--accent);
        font-family: var(--font-mono);
        font-size: 0.64rem;
        letter-spacing: 0.07em;
        padding: 0.18rem 0.45rem;
        text-align: center;
        text-transform: uppercase;
    }

    .type-tag-build {
        background: rgba(90,169,255,0.12);
        color: var(--info);
    }

    .type-tag-train {
        background: rgba(216,165,55,0.12);
        color: var(--warn);
    }

    .today-plan-title {
        color: var(--text);
        font-weight: 600;
        line-height: 1.25;
    }

    .today-plan-meta {
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 0.7rem;
        margin-top: 0.14rem;
    }

    .attention-list {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        background: var(--surface);
        padding: 0.35rem 0;
        animation: fadeUp .32s var(--ease) both;
    }

    .home-cockpit-head {
        margin-bottom: var(--s4);
        animation: fadeUp .32s var(--ease) both;
    }

    .home-cockpit-title {
        color: var(--text);
        font-family: var(--f-display);
        font-size: clamp(2rem, 4.5vw, 4.3rem);
        font-weight: 700;
        letter-spacing: 0;
        line-height: 0.95;
        margin: 0 0 var(--s2);
    }

    .home-cockpit-subtitle {
        max-width: 760px;
        color: var(--dim);
        font-size: 1rem;
        line-height: 1.6;
    }

    .home-plan-panel {
        border: 1px solid var(--border);
        border-radius: var(--r);
        background: var(--surface);
        padding: 0.2rem 0.95rem;
        margin-bottom: var(--s4);
        animation: fadeUp .32s var(--ease) both;
    }

    .home-stagger-1 {
        animation-delay: .04s;
    }

    .home-stagger-2 {
        animation-delay: .10s;
    }

    .home-stagger-3 {
        animation-delay: .16s;
    }

    .home-stagger-4 {
        animation-delay: .22s;
    }

    .attention-item {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 0.65rem;
        padding: 0.62rem 0.85rem;
        color: var(--dim);
        border-bottom: 1px solid var(--border-soft);
    }

    .attention-item:last-child {
        border-bottom: 0;
    }

    .attention-marker {
        color: var(--warn);
        font-family: var(--font-mono);
        font-size: 0.72rem;
    }

    .empty-state-line {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        background: var(--surface);
        color: var(--dim);
        padding: 0.85rem 1rem;
    }

    @media (max-width: 900px) {
        .home-resume-grid,
        .home-metric-grid {
            grid-template-columns: 1fr;
        }

        .today-plan-row {
            grid-template-columns: 1fr;
            align-items: start;
        }
    }

    .chip,
    .status-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 4px 10px;
        background: var(--surface-2);
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.06em;
        line-height: 1.35;
        text-transform: uppercase;
        vertical-align: middle;
    }

    .status-chip .dot,
    .status-chip .d,
    .chip-dot {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: currentColor;
    }

    .status-chip.pass,
    .status-chip-pass,
    .chip-pass,
    .chip-done,
    .chip-ready {
        color: var(--pass);
        background: rgba(79,208,106,0.12);
        border-color: rgba(79,208,106,0.35);
    }

    .status-chip.pass .chip-dot,
    .status-chip-pass .chip-dot,
    .chip-pass .chip-dot {
        box-shadow: 0 0 8px var(--pass);
        animation: pulse 1.8s var(--ease) infinite;
    }

    .status-chip.fail,
    .status-chip.error,
    .status-chip-fail,
    .status-chip-error,
    .chip-fail,
    .chip-error,
    .chip-blocked {
        color: var(--fail);
        background: rgba(255,94,84,0.12);
        border-color: rgba(255,94,84,0.35);
    }

    .chip-in-progress,
    .chip-needs-review,
    .chip-weak {
        color: var(--warn);
        background: rgba(216,165,55,0.10);
        border-color: rgba(216,165,55,0.30);
    }

    .status-chip.idle,
    .status-chip-idle,
    .chip-todo,
    .chip-not-started {
        color: var(--faint);
        background: var(--surface-2);
        border-color: var(--border);
    }

    .chip-info {
        color: var(--info);
        background: rgba(95,174,255,0.12);
        border-color: rgba(95,174,255,0.30);
    }

    .skeleton {
        display: flex;
        flex-direction: column;
        gap: 9px;
    }

    .sk,
    .skeleton-line {
        height: 12px;
        border-radius: 5px;
        background: linear-gradient(90deg, var(--surface-2) 0, #2A3140 40px, var(--surface-2) 80px);
        background-size: 360px 100%;
        animation: shimmer 1.1s linear infinite;
    }

    .run-result,
    .out {
        animation: fadeUp .35s var(--ease) both;
    }
</style>
        """,
        unsafe_allow_html=True,
    )


STATUS_CHIP_CLASSES = {
    "PASS": "status-chip-pass pass chip-pass",
    "FAIL": "status-chip-fail fail chip-fail",
    "ERROR": "status-chip-error error chip-error",
    "IN PROGRESS": "chip-in-progress",
    "DONE": "status-chip-pass pass chip-done",
    "NEEDS REVIEW": "chip-needs-review",
    "READY": "status-chip-pass pass chip-ready",
    "BLOCKED": "status-chip-error error chip-blocked",
}


def normalize_chip_status(status: str) -> str:
    normalized = re.sub(r"[_\-]+", " ", str(status or "").strip().upper())
    aliases = {
        "PASSED": "PASS",
        "FAILED": "FAIL",
        "DOING": "IN PROGRESS",
        "READING": "IN PROGRESS",
        "TODO": "IN PROGRESS",
        "TO DO": "IN PROGRESS",
        "NOT STARTED": "IN PROGRESS",
        "REVIEW": "NEEDS REVIEW",
        "WEAK": "NEEDS REVIEW",
        "NOT_STARTED": "IN PROGRESS",
        "NOTSTARTED": "IN PROGRESS",
        "IDLE": "READY",
        "COMPLETE": "DONE",
        "COMPLETED": "DONE",
    }
    return aliases.get(normalized, normalized or "IN PROGRESS")


def render_status_chip(status: str) -> str:
    label = normalize_chip_status(status)
    css_class = STATUS_CHIP_CLASSES.get(label, "chip-info")
    return (
        f'<span class="status-chip {css_class}">'
        f'<span class="chip-dot"></span>{html.escape(label)}</span>'
    )


def render_section_eyebrow(label: str) -> str:
    return f'<div class="eyebrow section-eyebrow">{html.escape(str(label))}</div>'


def render_section_eyebrow_block(label: str) -> None:
    st.markdown(render_section_eyebrow(label), unsafe_allow_html=True)


def render_metric_tile(
    label: str,
    value: str | int | float,
    *,
    total: str | int | float | None = None,
    progress: float | None = None,
    meta: str = "",
    status: str = "",
) -> str:
    total_markup = f'<span class="metric-tile-total">/{html.escape(str(total))}</span>' if total is not None else ""
    bar_markup = ""
    if progress is not None:
        width = max(0.0, min(1.0, float(progress))) * 100
        fill_class = ""
        if status:
            fill_status = normalize_chip_status(status).lower().replace(" ", "-")
            fill_class = f" metric-fill-{html.escape(fill_status)}"
        bar_markup = (
            '<div class="bar metric-bar">'
            f'<i class="metric-bar-fill{fill_class}" style="width: {width:.1f}%"></i>'
            "</div>"
        )
    meta_markup = f'<div class="metric-tile-meta">{html.escape(str(meta))}</div>' if meta else ""
    return (
        '<div class="metric-tile">'
        f'<div class="n metric-tile-value">{html.escape(str(value))}{total_markup}</div>'
        f'<div class="metric-tile-label">{html.escape(str(label))}</div>'
        f"{meta_markup}{bar_markup}"
        "</div>"
    )


def render_card(
    title: str,
    body: str = "",
    *,
    eyebrow: str = "",
    meta: str = "",
    status: str = "",
    extra_class: str = "",
    content_html: str = "",
) -> str:
    classes = " ".join(["console-card", str(extra_class or "").strip()]).strip()
    eyebrow_markup = f'<div class="console-card-eyebrow">{html.escape(str(eyebrow))}</div>' if eyebrow else ""
    status_markup = render_status_chip(status) if status else ""
    body_markup = f'<div class="console-card-body">{html.escape(str(body))}</div>' if body else ""
    meta_markup = f'<div class="console-card-meta">{html.escape(str(meta))}</div>' if meta else ""
    return (
        f'<div class="{html.escape(classes)}">'
        f"{eyebrow_markup}"
        f'<div class="console-card-title">{html.escape(str(title))} {status_markup}</div>'
        f"{body_markup}{meta_markup}{content_html}"
        "</div>"
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

    try:
        note_paths = sorted(vault.rglob("*.md"), key=lambda item: item.as_posix().casefold())
    except OSError:
        return {}

    for file_path in note_paths:
        if is_hidden_path(file_path, vault):
            continue

        try:
            section_key, display_name = get_section_for_file(file_path, vault)
            relative_path = file_path.relative_to(vault).as_posix()
        except (OSError, ValueError):
            continue
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
            "algorithm_attempts": {},
            "interview_answer_attempts": {},
            "mentor_tasks_status": {},
            "data_lab_projects": {},
        }

    try:
        data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "notes": {},
            "practice_status": {},
            "portfolio_outputs": {},
            "algos_status": {},
            "algorithm_attempts": {},
            "interview_answer_attempts": {},
            "mentor_tasks_status": {},
            "data_lab_projects": {},
        }

    if not isinstance(data, dict):
        return {
            "notes": {},
            "practice_status": {},
            "portfolio_outputs": {},
            "algos_status": {},
            "algorithm_attempts": {},
            "interview_answer_attempts": {},
            "mentor_tasks_status": {},
            "data_lab_projects": {},
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
    if not isinstance(data.get("algorithm_attempts"), dict):
        data["algorithm_attempts"] = {}
    if not isinstance(data.get("interview_answer_attempts"), dict):
        data["interview_answer_attempts"] = {}
    if not isinstance(data.get("mentor_tasks_status"), dict):
        data["mentor_tasks_status"] = {}
    if not isinstance(data.get("data_lab_projects"), dict):
        data["data_lab_projects"] = {}
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


def note_status_to_chip(status: str) -> str:
    return {
        STATUS_NOT_STARTED: "IN PROGRESS",
        STATUS_READING: "IN PROGRESS",
        STATUS_DONE: "PASS",
        STATUS_REPEAT: "NEEDS REVIEW",
    }.get(status, "IN PROGRESS")


def practice_status_to_chip(status: str) -> str:
    return {
        PRACTICE_TODO: "IN PROGRESS",
        PRACTICE_DOING: "IN PROGRESS",
        PRACTICE_DONE: "PASS",
    }.get(status, "IN PROGRESS")


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


def safe_widget_key(*parts: object) -> str:
    raw_parts: list[str] = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip()
        if text:
            raw_parts.append(text)
    raw_key = "_".join(raw_parts) or "widget"
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", raw_key).strip("_")
    if not cleaned:
        cleaned = "widget"
    if len(cleaned) <= 110:
        return cleaned
    digest = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:10]
    return f"{cleaned[:96].rstrip('_')}_{digest}"


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


def empty_link_graph() -> dict[str, Any]:
    return {
        "outgoing_by_path": {},
        "backlinks_by_path": {},
        "broken": [],
        "ambiguous": [],
        "summary": {
            "total": 0,
            "resolved": 0,
            "broken": 0,
            "ambiguous": 0,
        },
    }


@st.cache_data(show_spinner=False)
def scan_link_graph(vault_path: str) -> dict[str, Any]:
    try:
        vault = Path(vault_path).expanduser().resolve()
        sections = scan_vault(str(vault))
        note_index = build_note_index(sections)
    except OSError:
        return empty_link_graph()
    if not sections:
        return empty_link_graph()
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


def get_algorithm_attempts(lesson_id: str) -> list[dict[str, Any]]:
    progress = ensure_progress_state()
    attempts = progress.setdefault("algorithm_attempts", {}).get(lesson_id, [])
    return attempts if isinstance(attempts, list) else []


def save_algorithm_attempt(lesson_id: str, attempt: dict[str, Any]) -> None:
    progress = ensure_progress_state()
    record = normalize_algorithm_attempt({"lesson_id": lesson_id, **attempt})
    progress.setdefault("algorithm_attempts", {}).setdefault(lesson_id, []).append(record)
    save_progress(progress)


def interview_question_id(company: str, kind: str, index: int, text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", f"{company}-{kind}-{index}").strip("-").lower()
    digest = hashlib.sha1(str(text).encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def get_interview_attempts(question_id: str) -> list[dict[str, Any]]:
    progress = ensure_progress_state()
    attempts = progress.setdefault("interview_answer_attempts", {}).get(question_id, [])
    return attempts if isinstance(attempts, list) else []


def save_interview_attempt(question_id: str, attempt: dict[str, Any]) -> None:
    progress = ensure_progress_state()
    record = normalize_interview_answer_attempt({"question_id": question_id, **attempt})
    progress.setdefault("interview_answer_attempts", {}).setdefault(question_id, []).append(record)
    save_progress(progress)


def interview_arena_progress_summary() -> dict[str, int]:
    progress = ensure_progress_state()
    return summarize_interview_arena_progress(
        progress.get("algorithm_attempts", {}),
        progress.get("interview_answer_attempts", {}),
    )


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


def get_data_lab_project_record(project_id: str) -> dict[str, Any]:
    progress = ensure_progress_state()
    record = progress.setdefault("data_lab_projects", {}).get(project_id, {})
    return record if isinstance(record, dict) else {}


def is_data_lab_milestone_done(project_id: str, milestone_id: str) -> bool:
    return milestone_id in completed_milestone_ids(get_data_lab_project_record(project_id))


def get_data_lab_milestone_record(project_id: str, milestone_id: str) -> dict[str, Any]:
    return milestone_record(get_data_lab_project_record(project_id), milestone_id)


def set_data_lab_milestone_done(project_id: str, milestone_id: str, done: bool) -> None:
    progress = ensure_progress_state()
    record = get_data_lab_project_record(project_id)
    updated_record = set_milestone_completion(
        record,
        milestone_id,
        done,
    )
    if not done:
        updated_record = set_project_completion(updated_record, False)
    progress.setdefault("data_lab_projects", {})[project_id] = updated_record
    save_progress(progress)


def set_data_lab_milestone_updates(project_id: str, milestone_id: str, updates: dict[str, Any]) -> None:
    progress = ensure_progress_state()
    record = get_data_lab_project_record(project_id)
    progress.setdefault("data_lab_projects", {})[project_id] = set_milestone_data(record, milestone_id, updates)
    save_progress(progress)


def set_data_lab_milestone_checklist_item(
    project_id: str,
    milestone_id: str,
    item: str,
    checked: bool,
) -> None:
    progress = ensure_progress_state()
    record = get_data_lab_project_record(project_id)
    progress.setdefault("data_lab_projects", {})[project_id] = set_checklist_item(
        record,
        milestone_id,
        item,
        checked,
    )
    save_progress(progress)


def is_data_lab_project_complete(project_id: str) -> bool:
    return is_project_complete(get_data_lab_project_record(project_id))


def set_data_lab_project_complete(project: dict[str, Any], complete: bool) -> None:
    progress = ensure_progress_state()
    record = get_data_lab_project_record(project["id"])
    progress.setdefault("data_lab_projects", {})[project["id"]] = set_project_completion_if_ready(project, record, complete)
    save_progress(progress)


def data_lab_projects_progress(projects: list[dict[str, Any]]) -> dict[str, int]:
    total_milestones = 0
    done_milestones = 0
    done_projects = 0
    for project in projects:
        stats = project_progress_from_record(project, get_data_lab_project_record(project["id"]))
        total_milestones += stats["total"]
        done_milestones += stats["done"]
        if is_data_lab_project_complete(project["id"]):
            done_projects += 1
    return {
        "projects_total": len(projects),
        "projects_done": done_projects,
        "milestones_total": total_milestones,
        "milestones_done": done_milestones,
    }


@st.cache_data(show_spinner=False)
def scan_data_lab_projects() -> list[dict[str, Any]]:
    return load_project_recipes_from_dirs(PROJECT_RECIPE_DIRS)


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
    title = str(frontmatter.get("title") or note["display_name"])
    status = render_status_chip(note_status_to_chip(get_note_status(note)))
    header = f"""
<div class="note-header">
    {render_section_eyebrow("Theory note")}
    <div class="breadcrumbs">{html.escape(section_label)} / {html.escape(note["display_name"])}</div>
    <div class="note-header-title">{html.escape(title)} {status}</div>
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
        )
    else:
        st.button(
            f"{label} — не найдено",
            key=f"{prefix}_missing_{index}_{link.get('target')}",
            disabled=True,
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

    st.markdown(f'<div class="related-notes">{render_section_eyebrow("Граф заметки")}</div>', unsafe_allow_html=True)
    st.button(
        "🎲 Открыть случайную непройденную заметку",
        key="open_random_unstarted",
        on_click=open_random_unstarted,
        args=(sections,),
    )

    render_section_eyebrow_block("Исходящие ссылки")
    if outgoing_found:
        for index, link in enumerate(outgoing_found):
            render_link_card(link, index, "outgoing")
    else:
        st.caption("В этой заметке нет найденных исходящих ссылок.")

    if outgoing_missing:
        render_section_eyebrow_block("Не найдено")
        for index, link in enumerate(outgoing_missing):
            render_link_card(link, index, "outgoing_missing")

    render_section_eyebrow_block("Обратные ссылки / Backlinks")
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
    {render_section_eyebrow("Учебный статус")}
    <div class="muted-small">Отмечай состояние заметки, чтобы база становилась маршрутом, а не складом.</div>
    <div style="margin-top: 0.65rem;">{render_status_chip(note_status_to_chip(status))}</div>
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


def open_mentor_task(task: dict[str, Any]) -> None:
    st.session_state["selected_mentor_task"] = task["id"]
    if task.get("confidence") in {"high", "medium"}:
        st.session_state["mentor_task_notebook_filter"] = task.get("notebook_label", "Все")
        st.session_state["mentor_task_confidence_filter"] = task.get("confidence", "Все")
    st.session_state["active_tab"] = "🎯 Tasks"


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

    st.markdown(f'<div class="related-notes">{render_section_eyebrow("Практика по этой теме")}</div>', unsafe_allow_html=True)
    for card in related_cards:
        st.markdown(
            render_card(
                str(card["title"]),
                f"{card['section']} · {card['difficulty']} · {card['est_time']}",
                eyebrow="Practice card",
                status=practice_status_to_chip(get_card_status(card)),
            ),
            unsafe_allow_html=True,
        )
        st.button(
            "Открыть карточку",
            key=f"related_practice_{card['id']}",
            on_click=open_practice_card,
            args=(card["id"],),
        )


def semantic_search_note_item(note: dict[str, str]) -> SearchItem | None:
    text, error = read_note(note["path"])
    if error:
        return None
    frontmatter, body = split_frontmatter(text)
    title = str(frontmatter.get("title") or note.get("display_name") or note.get("relative_path") or "").strip()
    relative_path = str(note.get("relative_path") or note.get("display_name") or note.get("path") or "").strip()
    return SearchItem(
        source="theory_note",
        id=f"note:{relative_path}",
        title=title or relative_path,
        body=body,
        path=relative_path,
        payload={"display_name": note.get("display_name", ""), "section_key": note.get("section_key", "")},
    )


def semantic_search_practice_item(card: dict[str, Any]) -> SearchItem:
    body = "\n".join(
        [
            str(card.get("section") or ""),
            str(card.get("difficulty") or ""),
            str(card.get("related_note") or ""),
            str(card.get("dataset") or ""),
            str(card.get("body") or ""),
        ]
    )
    card_id = str(card.get("id") or "").strip()
    return SearchItem(
        source="practice",
        id=f"practice:{card_id}",
        title=str(card.get("title") or card_id),
        body=body,
        path=str(card.get("path") or ""),
        payload={"card_id": card_id},
    )


def semantic_search_task_item(task: dict[str, Any]) -> SearchItem:
    task_id = str(task.get("id") or "").strip()
    body = "\n".join(
        str(task.get(key) or "")
        for key in ("notebook_label", "prompt", "starter_code", "solution_starter", "test_code", "dependency_hint")
    )
    return SearchItem(
        source="task",
        id=f"task:{task_id}",
        title=str(task.get("title") or task_id),
        body=body,
        path=task_id,
        payload={"task_id": task_id, "notebook_label": task.get("notebook_label", "")},
    )


def build_semantic_search_index(
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
) -> SearchIndex:
    items: list[SearchItem] = []
    for note in all_notes(sections):
        item = semantic_search_note_item(note)
        if item is not None:
            items.append(item)
    items.extend(semantic_search_practice_item(card) for card in practice_cards)
    items.extend(semantic_search_task_item(task) for task in mentor_tasks)
    return build_search_index(items)


def semantic_search_result_status(
    result_source: str,
    result_path: str,
    result_payload: dict[str, Any],
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
) -> str:
    if result_source == "theory_note":
        note = note_from_relative_path_in_sections(result_path, sections)
        return note_status_to_chip(get_note_status(note)) if note else "NEEDS REVIEW"
    if result_source == "practice":
        card_id = str(result_payload.get("card_id") or "")
        card = next((candidate for candidate in practice_cards if candidate.get("id") == card_id), None)
        return practice_status_to_chip(get_card_status(card)) if card else "NEEDS REVIEW"
    if result_source == "task":
        task_id = str(result_payload.get("task_id") or "")
        return "PASS" if get_mentor_task_status(task_id) == STATUS_DONE else "IN PROGRESS"
    return "READY"


def semantic_search_source_label(source: str) -> str:
    return {
        "theory_note": "Theory",
        "practice": "Practice",
        "task": "Mentor Task",
    }.get(source, source)


def semantic_search_backend_label(index: SearchIndex) -> str:
    if index.backend == "embeddings":
        return f"embeddings · {index.model_name or 'local model'}"
    if index.reason == "embedding_backend_unavailable":
        return "TF-IDF · embeddings unavailable"
    return "TF-IDF"


def render_semantic_search_results(
    results: list[Any],
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
    *,
    key_prefix: str,
) -> None:
    task_by_id = {str(task.get("id")): task for task in mentor_tasks}
    for index, result in enumerate(results):
        score = f"score {result.score:.2f}"
        status = semantic_search_result_status(result.source, result.path, result.payload, sections, practice_cards)
        meta_parts = [score]
        if result.source == "theory_note" and result.path:
            meta_parts.append(result.path)
        elif result.source == "practice":
            meta_parts.append(result.payload.get("card_id", ""))
        elif result.source == "task":
            meta_parts.append(str(result.payload.get("notebook_label") or "Mentor task"))
        st.markdown(
            render_card(
                result.title,
                " · ".join(part for part in meta_parts if part),
                eyebrow=semantic_search_source_label(result.source),
                status=status,
            ),
            unsafe_allow_html=True,
        )
        button_key = safe_widget_key(key_prefix, result.source, result.id, index)
        if result.source == "theory_note":
            st.button(
                "Открыть заметку",
                key=button_key,
                on_click=open_theory_note_path,
                args=(result.path, sections),
            )
        elif result.source == "practice":
            card_id = str(result.payload.get("card_id") or "")
            st.button(
                "Открыть practice card",
                key=button_key,
                on_click=open_practice_card,
                args=(card_id,),
                disabled=not any(card.get("id") == card_id for card in practice_cards),
            )
        elif result.source == "task":
            task_id = str(result.payload.get("task_id") or "")
            task = task_by_id.get(task_id)
            st.button(
                "Открыть mentor task",
                key=button_key,
                on_click=open_mentor_task,
                args=(task,),
                disabled=task is None,
            )


def render_theory_search_box(
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
) -> None:
    render_section_eyebrow_block("Find related")
    st.markdown(
        render_card(
            "Локальный semantic search",
            "Поиск ищет по заметкам vault, practice cards и mentor tasks. По умолчанию используется TF-IDF; embeddings включаются только через HUBML_EMBEDDINGS=1.",
            eyebrow="Local search",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Поиск по смыслу",
        key="semantic_search_query",
        placeholder="Например: pandas groupby, leakage, window function",
    )
    if st.button("Обновить индекс поиска", key="semantic_search_refresh"):
        with st.spinner("Собираю локальный TF-IDF индекс..."):
            index = build_semantic_search_index(sections, practice_cards, mentor_tasks)
        st.session_state[SEMANTIC_SEARCH_INDEX_KEY] = index
        st.session_state[SEMANTIC_SEARCH_META_KEY] = {
            "items": len(index.items),
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        st.success(f"Индекс обновлён: {len(index.items)} документов · {semantic_search_backend_label(index)}")

    index = st.session_state.get(SEMANTIC_SEARCH_INDEX_KEY)
    meta = st.session_state.get(SEMANTIC_SEARCH_META_KEY, {})
    if not isinstance(index, SearchIndex):
        st.markdown(
            render_card(
                "Индекс ещё не собран",
                "Нажми «Обновить индекс поиска», чтобы построить локальный индекс. Автосканирования на загрузке нет.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return

    st.caption(f"Backend: {semantic_search_backend_label(index)} · Документов в индексе: {meta.get('items', len(index.items))}")
    if not query.strip():
        return

    results = semantic_search(index, query, k=6)
    if not results:
        st.markdown(
            render_card(
                "Совпадений нет",
                "Попробуй другой запрос: тему, библиотеку, метрику или название датасета.",
                eyebrow="Search",
                status="NEEDS REVIEW",
            ),
            unsafe_allow_html=True,
        )
        return
    render_semantic_search_results(results, sections, practice_cards, mentor_tasks, key_prefix="semantic_search")


def render_related_semantic_results(
    note: dict[str, str],
    body: str,
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
) -> None:
    index = st.session_state.get(SEMANTIC_SEARCH_INDEX_KEY)
    if not isinstance(index, SearchIndex):
        return
    query = f"{note.get('display_name', '')}\n{body[:1200]}"
    current_id = f"note:{note.get('relative_path', '')}"
    results = semantic_search(index, query, k=4, exclude_ids={current_id})
    if not results:
        return
    render_section_eyebrow_block("Related by semantic search")
    render_semantic_search_results(results, sections, practice_cards, mentor_tasks, key_prefix="semantic_related")


def render_note(
    section_key: str,
    note: dict[str, str],
    vault: Path,
    note_index: dict[str, Any],
    graph: dict[str, Any],
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
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

    render_related_semantic_results(note, body, sections, practice_cards, mentor_tasks)
    render_related_practice_block(note, practice_cards, note_index)
    render_graph_navigation(note, graph, sections)


def open_note_from_roadmap(note: dict[str, str]) -> None:
    set_active_note(note, push_history=False)
    st.session_state["active_tab"] = "Theory"


def normalize_home_note_target(note: dict[str, str]) -> dict[str, str]:
    relative_path = str(note.get("relative_path") or note.get("display_name") or note.get("path") or "").strip()
    if note.get("section_key") and note.get("display_name"):
        label = link_path_label(note)
    elif note.get("section_label") and note.get("display_name"):
        label = f"{note['section_label']} / {note['display_name']}"
    else:
        label = relative_path
    return {
        "kind": "learn",
        "label": label,
        "path": relative_path,
        "tab": "Theory",
    }


def note_from_relative_path_in_sections(
    relative_path: str,
    sections: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    wanted = str(relative_path or "").strip().casefold()
    if not wanted:
        return None
    for note in all_notes(sections):
        if str(note.get("relative_path", "")).casefold() == wanted:
            return note
    return None


def open_theory_note_path(relative_path: str, sections: dict[str, list[dict[str, str]]]) -> None:
    note = note_from_relative_path_in_sections(relative_path, sections)
    if note is not None:
        set_active_note(note, push_history=False)
    st.session_state["active_tab"] = "Theory"


def open_tab(tab_name: str) -> None:
    st.session_state["active_tab"] = tab_name


def nav_button_label(tab_name: str) -> str:
    icon = NAV_ICONS.get(tab_name, "·")
    label = NAV_LABELS.get(tab_name, tab_name)
    return f"{icon} {label}"


def render_nav_active_row(tab_name: str) -> None:
    icon = NAV_ICONS.get(tab_name, "·")
    label = NAV_LABELS.get(tab_name, tab_name)
    st.sidebar.markdown(
        f"""
<div class="nav-active-row">
    <span class="nav-ico">{html.escape(icon)}</span>
    <span>{html.escape(label)}</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_grouped_navigation() -> str:
    active_tab = st.session_state.get("active_tab", "Home")
    if active_tab not in TAB_OPTIONS:
        active_tab = "Home"
        st.session_state["active_tab"] = active_tab

    st.sidebar.markdown("### Hub_ML")
    st.sidebar.caption("local ML workstation")
    for group, items in NAV_GROUPS:
        st.sidebar.markdown(
            f'<div class="nav-group-label">{html.escape(group)}</div>',
            unsafe_allow_html=True,
        )
        for tab_name, _, _ in items:
            if tab_name == active_tab:
                render_nav_active_row(tab_name)
                continue
            st.sidebar.button(
                nav_button_label(tab_name),
                key=f"nav_{tab_name}",
                on_click=open_tab,
                args=(tab_name,),
                use_container_width=True,
            )
    return active_tab


def render_breadcrumb(active_tab: str) -> None:
    group = NAV_GROUP_BY_TAB.get(active_tab, "Home")
    label = NAV_LABELS.get(active_tab, active_tab)
    if active_tab == "Home":
        crumb = '<span class="ctx">Home</span>'
    else:
        crumb = (
            f"<span>{html.escape(group)}</span><span class=\"sep\">/</span>"
            f"<span class=\"ctx\">{html.escape(label)}</span>"
        )
    st.markdown(
        f"""
<div class="ide-topbar breadcrumb-shell">
    <div class="ide-topbar-left">{crumb}</div>
    <div class="ide-topbar-right">Jump… ⌘K</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def git_branch_from_head(git_dir: Path | None = None) -> str:
    git_dir = git_dir or PROJECT_ROOT / ".git"
    head_path = git_dir / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "main"
    if head.startswith("ref:"):
        return Path(head.removeprefix("ref:").strip()).name or "main"
    return head[:7] if head else "main"


def content_gate_status(report_path: Path = CONTENT_GATE_REPORT_PATH) -> str:
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "GATE n/a"
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return "GATE n/a"
    passed = summary.get("passed_topics")
    total = summary.get("total_topics", 36)
    if isinstance(passed, list):
        passed = len(passed)
    try:
        return f"GATE {int(passed)}/{int(total)}"
    except (TypeError, ValueError):
        return "GATE n/a"


def notebook_kernel_status_label() -> str:
    kernel_state = st.session_state.get("notebook_kernel_state")
    if not isinstance(kernel_state, dict):
        return "unknown"
    status = str(kernel_state.get("status") or "unknown").lower()
    if status in {"idle", "busy", "dead", "error"}:
        return status
    return "unknown"


def render_status_bar() -> None:
    kernel_status = notebook_kernel_status_label()
    branch = git_branch_from_head()
    gate = content_gate_status()
    python_label = f"python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    st.markdown(
        f"""
<div class="ide-statusbar">
    <div class="ide-statusbar-left">
        <span class="ide-statusbar-item"><span class="ide-statusbar-dot {html.escape(kernel_status)}"></span>kernel {html.escape(kernel_status)}</span>
        <span class="ide-statusbar-item">git {html.escape(branch)}</span>
        <span class="ide-statusbar-item">{html.escape(gate)}</span>
        <span class="ide-statusbar-item">{html.escape(python_label)}</span>
    </div>
    <div class="ide-statusbar-right">local-first · код виден · без фейковых метрик</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_vault_setup_card(title: str, body: str, *, status: str = "IN PROGRESS") -> None:
    st.markdown(
        render_card(
            title,
            body,
            eyebrow="Vault setup",
            status=status,
            content_html=(
                '<div class="console-panel">'
                '<div class="phead"><span class="dot3"><i></i><i></i><i></i></span><span>setup · VAULT_PATH</span></div>'
                '<div class="editor mono">VAULT_PATH="/absolute/path/to/obsidian_vault" streamlit run app.py</div>'
                "</div>"
            ),
        ),
        unsafe_allow_html=True,
    )


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


def open_project_tab(project_id: str, tab_name: str = "🧪 Data Lab Projects") -> None:
    st.session_state["selected_data_lab_project"] = project_id
    st.session_state["active_tab"] = tab_name


def open_algorithm_lesson(lesson_id: str) -> None:
    st.session_state["selected_algorithm_lesson"] = lesson_id
    st.session_state["active_tab"] = "🧩 Algorithms"


def next_mentor_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        task
        for task in tasks
        if task.get("confidence") != "low" and get_mentor_task_status(task["id"]) != STATUS_DONE
    ]
    return candidates[0] if candidates else None


def next_project_milestone(projects: list[dict[str, Any]]) -> dict[str, Any] | None:
    for project in projects:
        completed = completed_milestone_ids(get_data_lab_project_record(project["id"]))
        for milestone in project.get("milestones", []):
            if not isinstance(milestone, dict):
                continue
            milestone_id = str(milestone.get("id") or "")
            if milestone_id and milestone_id not in completed:
                return {"project": project, "milestone": milestone}
    return None


def experiment_records_for_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for project in projects:
        workspace_path = project_workspace_path(project, USER_PROJECTS_DIR)
        records_path = experiment_records_path(workspace_path)
        for record in load_experiment_records(records_path):
            records.append({**record, "project_title": project.get("title", project.get("id", ""))})
    records.sort(key=lambda record: str(record.get("timestamp") or ""), reverse=True)
    return records


def first_algorithm_to_practice(lessons: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((lesson for lesson in lessons if get_algorithm_status(lesson["id"]) != STATUS_DONE), None)


def first_interview_prompt(interview_data: dict[str, Any]) -> dict[str, str] | None:
    for company in interview_data.get("companies", []):
        questions = company.get("questions") or []
        if questions:
            return {"company": str(company.get("company") or "Interview"), "text": str(questions[0])}
    return None


def theory_quality_average(audit_report: dict[str, Any]) -> float | None:
    summary = theory_summary(audit_report)
    value = summary.get("average_quality_score")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def render_today_plan_row(
    *,
    kind: str,
    title: str,
    meta: str,
    status: str,
    button_label: str,
    button_key: str,
    on_click: Any,
    args: tuple[Any, ...] = (),
) -> None:
    kind_class = {
        "learn": "type-tag",
        "build": "type-tag type-tag-build",
        "train": "type-tag type-tag-train",
    }.get(kind, "type-tag")
    st.markdown(
        f"""
<div class="today-plan-row home-stagger-2">
    <span class="{kind_class}">{html.escape(kind)}</span>
    <span>
        <div class="today-plan-title">{html.escape(title)}</div>
        <div class="today-plan-meta">{html.escape(meta)}</div>
    </span>
    <span>{render_status_chip(status)}</span>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.button(button_label, key=button_key, on_click=on_click, args=args)


def render_attention_item(label: str, marker: str = "WARN") -> str:
    return (
        '<div class="attention-item">'
        f'<span class="attention-marker">{html.escape(marker)}</span>'
        f'<span>{html.escape(label)}</span>'
        "</div>"
    )


def render_dashboard(
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    datasets: list[dict[str, Any]],
    graph: dict[str, Any],
    mentor_data: dict[str, Any],
    data_lab_projects: list[dict[str, Any]],
    algorithm_lessons: list[dict[str, Any]],
    interview_data: dict[str, Any],
    audit_report: dict[str, Any],
    coverage_report: dict[str, Any],
) -> None:
    notes = all_notes(sections)
    total_notes = len(notes)
    next_note = find_next_note(sections)
    next_card = next_practice_card(practice_cards)
    mentor_tasks = mentor_data.get("tasks", [])
    next_task = next_mentor_task(mentor_tasks)
    project_step = next_project_milestone(data_lab_projects)
    next_algorithm = first_algorithm_to_practice(algorithm_lessons)
    interview_prompt = first_interview_prompt(interview_data)
    graph_summary = graph["summary"]
    mentor_stats = mentor_tasks_progress(mentor_tasks)
    project_stats = data_lab_projects_progress(data_lab_projects)
    experiment_records = experiment_records_for_projects(data_lab_projects)
    quality_avg = theory_quality_average(audit_report)
    next_note_target = normalize_home_note_target(next_note) if next_note else None

    st.markdown(
        """
<div class="home-cockpit-head">
    <div class="home-cockpit-title">Hub_ML</div>
    <div class="home-cockpit-subtitle">Инженерная консоль для локальной ML-практики: учиться, собирать проекты, тренироваться и готовить portfolio artifacts.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    resume_cards: list[str] = []
    if next_task:
        resume_cards.append(
            render_card(
                next_task["title"],
                f"{next_task['notebook_label']} · confidence {next_task['confidence']}",
                eyebrow="Следующая задача ментора",
                meta=f"решено: {mentor_stats['done']}/{mentor_stats['total']}",
                status="TODO",
            )
        )
    else:
        resume_cards.append(render_card("Задачи ментора закрыты", "Нет открытой проверяемой задачи.", eyebrow="Следующая задача ментора", status="PASS"))

    if project_step:
        project = project_step["project"]
        milestone = project_step["milestone"]
        resume_cards.append(
            render_card(
                str(milestone.get("title") or milestone.get("id") or "Project milestone"),
                str(project.get("title") or project.get("id") or "Project"),
                eyebrow="Следующий milestone проекта",
                meta=f"тип: {milestone.get('type', 'milestone')}",
                status="IN PROGRESS",
            )
        )
    else:
        resume_cards.append(render_card("Проекты закрыты", "Все обязательные milestones завершены.", eyebrow="Следующий milestone проекта", status="PASS"))

    if next_note and next_note_target:
        resume_cards.append(
            render_card(
                next_note_target["label"],
                f"заметок в vault: {len(notes)}",
                eyebrow="Следующая theory note",
                meta=next_note_target["path"],
                status="READING" if get_note_status(next_note) == STATUS_READING else "TODO",
            )
        )
    else:
        resume_cards.append(render_card("Теория закрыта", f"просмотрено заметок: {total_notes}", eyebrow="Следующая theory note", status="PASS"))

    render_section_eyebrow_block("Продолжить")
    st.markdown(f'<div class="home-resume-grid home-stagger-1">{"".join(resume_cards)}</div>', unsafe_allow_html=True)

    render_section_eyebrow_block("План на сегодня")
    today_count = 0
    if next_note and next_note_target and today_count < 4:
        render_today_plan_row(
            kind=next_note_target["kind"],
            title=next_note_target["label"],
            meta=next_note_target["path"],
            status="READING" if get_note_status(next_note) == STATUS_READING else "TODO",
            button_label="Открыть теорию",
            button_key="home_today_note",
            on_click=open_theory_note_path,
            args=(next_note_target["path"], sections),
        )
        today_count += 1
    if next_card and today_count < 4:
        render_today_plan_row(
            kind="learn",
            title=next_card["title"],
            meta=f"{next_card['section']} · {next_card['difficulty']} · {next_card['est_time']}",
            status="IN PROGRESS" if get_card_status(next_card) == PRACTICE_DOING else "TODO",
            button_label="Открыть практику",
            button_key="home_today_practice",
            on_click=open_practice_card,
            args=(next_card["id"],),
        )
        today_count += 1
    if project_step and today_count < 4:
        project = project_step["project"]
        milestone = project_step["milestone"]
        project_tab = "🤖 ML Lab" if str(project.get("track") or "").casefold() == "classic ml" else "🧪 Data Lab Projects"
        render_today_plan_row(
            kind="build",
            title=str(milestone.get("title") or milestone.get("id") or "Project milestone"),
            meta=str(project.get("title") or project.get("id") or "Project"),
            status="IN PROGRESS",
            button_label="Открыть проект",
            button_key="home_today_project",
            on_click=open_project_tab,
            args=(project["id"], project_tab),
        )
        today_count += 1
    if next_task and today_count < 4:
        render_today_plan_row(
            kind="train",
            title=next_task["title"],
            meta=next_task["notebook_label"],
            status="TODO",
            button_label="Открыть задачу",
            button_key="home_today_task",
            on_click=open_mentor_task,
            args=(next_task,),
        )
        today_count += 1
    if next_algorithm and today_count < 4:
        render_today_plan_row(
            kind="train",
            title=next_algorithm["title"],
            meta="Algorithms Lab",
            status="TODO",
            button_label="Открыть алгоритм",
            button_key="home_today_algorithm",
            on_click=open_algorithm_lesson,
            args=(next_algorithm["id"],),
        )
        today_count += 1
    if today_count == 0 and interview_prompt:
        render_today_plan_row(
            kind="train",
            title=f"Interview-вопрос: {interview_prompt['company']}",
            meta=interview_prompt["text"][:120],
            status="TODO",
            button_label="Открыть Interviews",
            button_key="home_today_interview",
            on_click=open_tab,
            args=("🎤 Interviews",),
        )
        today_count += 1
    if today_count == 0:
        st.markdown('<div class="empty-state-line">Нет готового следующего шага. Открой Projects или Theory и выбери направление.</div>', unsafe_allow_html=True)

    render_section_eyebrow_block("Статус")
    task_ratio = mentor_stats["done"] / mentor_stats["total"] if mentor_stats["total"] else 0.0
    project_ratio = project_stats["projects_done"] / project_stats["projects_total"] if project_stats["projects_total"] else 0.0
    metric_tiles = [
        render_metric_tile(
            "Задачи решены",
            mentor_stats["done"],
            total=mentor_stats["total"],
            progress=task_ratio,
            status="PASS" if task_ratio == 1 else "IN PROGRESS",
        ),
        render_metric_tile(
            "Проекты завершены",
            project_stats["projects_done"],
            total=project_stats["projects_total"],
            progress=project_ratio,
            meta=f"milestones: {project_stats['milestones_done']}/{project_stats['milestones_total']}",
            status="PASS" if project_ratio == 1 and project_stats["projects_total"] else "IN PROGRESS",
        ),
    ]
    if experiment_records:
        latest = experiment_records[0].get("timestamp", "")
        metric_tiles.append(render_metric_tile("Experiment runs", len(experiment_records), meta=f"последний: {latest[:10]}", status="INFO"))
    else:
        metric_tiles.append(render_metric_tile("Experiment runs", "—", meta="нет сохранённых запусков", status="WEAK"))
    if quality_avg is not None:
        metric_tiles.append(
            render_metric_tile(
                "Среднее качество теории",
                f"{quality_avg:.1f}",
                total=100,
                progress=quality_avg / 100,
                status="PASS" if quality_avg >= 70 else "WEAK",
            )
        )
    else:
        metric_tiles.append(render_metric_tile("Среднее качество теории", "—", meta="нет theory audit report", status="WEAK"))
    st.markdown(f'<div class="home-metric-grid home-stagger-3">{"".join(metric_tiles)}</div>', unsafe_allow_html=True)

    render_section_eyebrow_block("Требует внимания")
    attention: list[str] = []
    if not audit_report:
        attention.append("Нет theory audit report. Запусти аудит вручную из Theory Quality.")
    if not coverage_report:
        attention.append("Нет coverage report. Запусти coverage check вручную.")
    if audit_report:
        weak = [note for note in weakest_notes(audit_report, limit=20) if int(note.get("quality_score") or 0) < 45]
        if weak:
            attention.append(f"В текущем audit top 20 есть слабые theory notes: {len(weak)}.")
    incomplete_milestones = project_stats["milestones_total"] - project_stats["milestones_done"]
    if incomplete_milestones:
        attention.append(f"Открытые project milestones: {incomplete_milestones}.")
    if not experiment_records:
        attention.append("Пока нет experiment records. Сохрани реальный run из Classic ML project.")
    if graph_summary.get("broken"):
        attention.append(f"Broken Obsidian links требуют проверки: {graph_summary['broken']}.")
    if not datasets:
        attention.append("В datasets/ не найдены CSV. Добавь данные перед Data Lab.")

    if attention:
        st.markdown(
            '<div class="attention-list home-stagger-4">'
            + "".join(render_attention_item(item) for item in attention)
            + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            render_card(
                "Срочных проблем нет",
                "По текущим reports и progress всё выглядит спокойно.",
                eyebrow="Needs attention",
                status="READY",
                extra_class="home-stagger-4",
            ),
            unsafe_allow_html=True,
        )


def render_roadmap(sections: dict[str, list[dict[str, str]]]) -> None:
    st.markdown(
        render_card(
            "Roadmap",
            "Это учебная карта поверх Obsidian: проходи разделы, открывай заметки и отмечай прогресс.",
            eyebrow="Learn cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    next_note = find_next_note(sections)
    if next_note:
        section_label = humanize_section_name(next_note["section_key"])
        st.markdown(
            render_card(
                "Следующий разумный шаг",
                f"{section_label} / {next_note['display_name']}",
                eyebrow="Next note",
                status=note_status_to_chip(get_note_status(next_note)),
            ),
            unsafe_allow_html=True,
        )
        st.button(
            "Открыть следующую заметку",
            key="open_next_note",
            on_click=open_note_from_roadmap,
            args=(next_note,),
        )
    else:
        st.markdown(
            render_card(
                "Все заметки отмечены",
                "Красиво идем. Можно открыть Practice или Projects.",
                eyebrow="Roadmap",
                status="PASS",
            ),
            unsafe_allow_html=True,
        )

    render_section_eyebrow_block("Разделы")
    for section_key, notes in sections.items():
        stats = section_progress(notes)
        done = stats[STATUS_DONE]
        reading = stats[STATUS_READING]
        repeat = stats[STATUS_REPEAT]
        total = stats["total"]
        ratio = done / total if total else 0.0

        st.markdown(
            render_card(
                humanize_section_name(section_key),
                f"{done}/{total} готово · {reading} читаю · {repeat} повторить",
                eyebrow="Vault section",
                status="PASS" if ratio == 1 and total else "IN PROGRESS",
                content_html=render_metric_tile(
                    "Progress",
                    done,
                    total=total,
                    progress=ratio,
                    status="PASS" if ratio == 1 and total else "IN PROGRESS",
                ),
            ),
            unsafe_allow_html=True,
        )

        with st.expander(f"Заметки раздела: {humanize_section_name(section_key)}"):
            for note in notes:
                cols = st.columns([0.52, 0.22, 0.26])
                cols[0].markdown(
                    f"{html.escape(note['display_name'])}",
                    unsafe_allow_html=True,
                )
                cols[1].markdown(render_status_chip(note_status_to_chip(get_note_status(note))), unsafe_allow_html=True)
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
        render_card(
            str(card["title"]),
            f"{card['section']} · {card['difficulty']} · {card['est_time']}{dataset}",
            eyebrow="Practice card",
            status=practice_status_to_chip(get_card_status(card)),
        ),
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

    render_section_eyebrow_block("Portfolio output")
    if flash_message == "saved":
        st.success("Output сохранён.")
    st.markdown(
        render_card(
            "Что останется после задачи",
            "Коротко зафиксируй результат, путь к артефакту и вывод. Это не проверка, а след работы.",
            eyebrow="Output",
            status="READY" if output_has_content(record) else "TODO",
        ),
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

    st.markdown(
        render_card(
            str(card["title"]),
            f"{card['section']} · {card['difficulty']} · {card['est_time']}",
            eyebrow="Practice detail",
            status=practice_status_to_chip(get_card_status(card)),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(render_frontmatter_chips(chips), unsafe_allow_html=True)
    render_external_links(card.get("links", []))

    related_note = resolve_related_note(str(card.get("related_note") or ""), note_index)
    if related_note:
        st.button(
            "📖 Открыть теорию",
            key=f"practice_open_theory_{card['id']}",
            on_click=open_theory_note,
            args=(related_note,),
        )
    elif card.get("related_note"):
        st.markdown(
            render_card(
                "Связанная заметка не найдена",
                str(card["related_note"]),
                eyebrow="Needs review",
                status="NEEDS REVIEW",
            ),
            unsafe_allow_html=True,
        )

    if card.get("dataset"):
        dataset = find_dataset_record(card["dataset"], datasets)
        st.button(
            "📊 Открыть датасет",
            key=f"practice_open_dataset_{card['id']}",
            on_click=open_dataset_from_card,
            args=(card["dataset"], card["id"]),
            disabled=dataset is None,
        )
        st.button(
            "📓 Открыть в Notebook",
            key=f"practice_open_notebook_{card['id']}",
            on_click=open_dataset_in_notebook,
            args=(card["dataset"],),
            disabled=dataset is None,
        )
        if dataset is None:
            st.markdown(
                render_card(
                    "Dataset не найден",
                    f"Файл {card['dataset']} пока не найден в datasets/.",
                    eyebrow="Needs review",
                    status="NEEDS REVIEW",
                ),
                unsafe_allow_html=True,
            )

    render_section_eyebrow_block("Инструкция")
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
    st.markdown(
        render_card(
            "🎯 Practice",
            "Карточки превращают теорию в действие: инструкция, ресурсы, самопроверка и портфолио-выход.",
            eyebrow="Learn cluster",
            status="READY" if cards else "TODO",
        ),
        unsafe_allow_html=True,
    )

    for warning in warnings:
        st.markdown(
            render_card(
                "Practice warning",
                warning,
                eyebrow="Needs review",
                status="NEEDS REVIEW",
            ),
            unsafe_allow_html=True,
        )

    if not cards:
        st.markdown(
            render_card(
                "Practice cards не найдены",
                "Добавь markdown-карточки в practice/, чтобы связать теорию с действием.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return

    stats = practice_progress(cards)
    done_ratio = stats[PRACTICE_DONE] / stats["total"] if stats["total"] else 0.0
    metric_tiles = [
        render_metric_tile("Карточек", stats["total"], status="INFO"),
        render_metric_tile("В работе", stats[PRACTICE_DOING], status="IN PROGRESS"),
        render_metric_tile(
            "Сделано",
            stats[PRACTICE_DONE],
            total=stats["total"],
            progress=done_ratio,
            status="PASS" if done_ratio == 1 else "IN PROGRESS",
        ),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(metric_tiles)}</div>', unsafe_allow_html=True)

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
        st.markdown(
            render_card(
                "По таким фильтрам карточек нет",
                "Смени section/difficulty или сбрось фильтры на «Все».",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return

    selected_id = st.session_state.get("selected_practice_card")
    if selected_id not in {card["id"] for card in filtered}:
        selected_id = filtered[0]["id"]
        st.session_state["selected_practice_card"] = selected_id

    list_col, detail_col = st.columns([0.38, 0.62], gap="large")
    with list_col:
        render_section_eyebrow_block("Карточки")
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


def select_data_lab_project(project_id: str) -> None:
    st.session_state["selected_data_lab_project"] = project_id


def find_practice_card(card_id: str, cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    wanted = str(card_id or "").strip()
    if not wanted:
        return None
    wanted_stem = Path(wanted).stem
    return next(
        (
            card
            for card in cards
            if str(card.get("id") or "") == wanted
            or Path(str(card.get("id") or "")).stem == wanted_stem
        ),
        None,
    )


def related_mentor_tasks(task_ref: str, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = str(task_ref or "").strip()
    if not wanted:
        return []
    wanted_key = wanted.casefold()
    matches: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task.get("id") or "")
        source_notebook = Path(str(task.get("source_notebook") or "")).stem
        notebook_label = str(task.get("notebook_label") or "")
        if task_id.casefold() == wanted_key:
            return [task]
        if source_notebook.casefold() == wanted_key or notebook_label.casefold() == wanted_key:
            matches.append(task)
    return sorted(matches, key=lambda item: str(item.get("title", "")).casefold())


def first_related_mentor_task(task_ref: str, tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = related_mentor_tasks(task_ref, tasks)
    return matches[0] if matches else None


def project_readiness_checks(
    project: dict[str, Any],
    *,
    note_index: dict[str, Any],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
    datasets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    for theory_path in project.get("related_theory_paths", []):
        note = note_from_relative_path(str(theory_path), note_index) or resolve_related_note(str(theory_path), note_index)
        checks.append(
            {
                "kind": "Theory",
                "label": str(theory_path),
                "done": bool(note and get_note_status(note) == STATUS_DONE),
            }
        )

    for card_id in project.get("related_practice_ids", []):
        card = find_practice_card(str(card_id), practice_cards)
        label = str(card.get("title") if card else card_id)
        checks.append(
            {
                "kind": "Practice",
                "label": label,
                "done": bool(card and get_card_status(card) == PRACTICE_DONE),
            }
        )

    for task_ref in project.get("related_task_ids", []):
        related_tasks = related_mentor_tasks(str(task_ref), mentor_tasks)
        done = bool(related_tasks) and any(get_mentor_task_status(task["id"]) == STATUS_DONE for task in related_tasks)
        label = f"{task_ref} ({len(related_tasks)} tasks)" if related_tasks else str(task_ref)
        checks.append({"kind": "Tasks", "label": label, "done": done})

    for dataset_name in project.get("related_dataset_names", []):
        checks.append(
            {
                "kind": "Datasets",
                "label": str(dataset_name),
                "done": find_dataset_record(str(dataset_name), datasets) is not None,
            }
        )

    return checks


def render_readiness_badge(readiness: dict[str, Any]) -> str:
    status = str(readiness.get("status") or "not ready")
    if status == "ready":
        css_class = "status-done"
        label = "ready"
    elif status == "almost ready":
        css_class = "status-reading"
        label = "almost ready"
    else:
        css_class = "status-repeat"
        label = "not ready"
    return f'<span class="status-pill {css_class}">{html.escape(label)}</span>'


def render_project_progress_badge(stats: dict[str, Any]) -> str:
    label = f"{stats['done']}/{stats['total']} milestones"
    status = "PASS" if stats["total"] and stats["done"] == stats["total"] else "IN PROGRESS"
    return f"{render_status_chip(status)} <span class='muted-small'>{html.escape(label)}</span>"


def render_data_lab_project_card(project: dict[str, Any]) -> None:
    stats = project_progress_from_record(project, get_data_lab_project_record(project["id"]))
    datasets = ", ".join(project.get("datasets", [])) or "no datasets"
    skills = " · ".join(project.get("skills", [])[:4])
    st.markdown(
        render_card(
            str(project["title"]),
            f"{project['level']} · {datasets}",
            eyebrow="Project",
            meta=skills,
            status="PASS" if stats["total"] and stats["done"] == stats["total"] else "IN PROGRESS",
            content_html=render_metric_tile(
                "Milestones",
                stats["done"],
                total=stats["total"],
                progress=stats["ratio"],
                status="PASS" if stats["total"] and stats["done"] == stats["total"] else "IN PROGRESS",
            ),
        ),
        unsafe_allow_html=True,
    )
    st.button(
        "Открыть проект",
        key=f"data_lab_select_{project['id']}",
        on_click=select_data_lab_project,
        args=(project["id"],),
    )


def project_milestone_widget_key(project_id: str, milestone_id: str, suffix: str) -> str:
    return safe_widget_key("project_milestone", project_id, milestone_id, suffix)


def render_project_milestone_result(result: dict[str, Any]) -> None:
    classification = str(result.get("classification") or classify_task_result(result))
    elapsed = float(result.get("elapsed") or 0)
    st.markdown(
        f"""
<div class="run-result console-card">
    <div class="console-card-eyebrow">Milestone result</div>
    <div class="console-card-title">{render_status_chip(classification)} <span class="muted-small">kernel · {elapsed:.2f}s</span></div>
</div>
        """,
        unsafe_allow_html=True,
    )
    render_mentor_task_result(result)
    rich_outputs = [
        output
        for output in result.get("outputs", [])
        if isinstance(output, dict) and output.get("type") in {"execute_result", "display_data"}
    ]
    if rich_outputs:
        st.markdown("##### Rich output")
        for output in rich_outputs:
            render_notebook_output(output)


def render_project_code_runner(project: dict[str, Any], milestone: dict[str, Any], record: dict[str, Any]) -> None:
    project_id = project["id"]
    milestone_id = milestone["id"]
    code_key = project_milestone_widget_key(project_id, milestone_id, "code")
    result_key = project_milestone_widget_key(project_id, milestone_id, "last_result")
    starter_code = str(milestone.get("starter_code") or "")
    if code_key not in st.session_state:
        st.session_state[code_key] = str(record.get("solution_code") or starter_code)

    st.markdown(
        """
<div class="console-panel">
    <div class="phead"><span class="dot3"><i></i><i></i><i></i></span><span>python · project milestone</span></div>
</div>
        """,
        unsafe_allow_html=True,
    )
    render_section_eyebrow_block("Solution code")
    use_plain_editor = st.session_state.get("project_milestones_plain_editor", False) or st_ace is None
    if st_ace is not None and not use_plain_editor:
        code = st_ace(
            value=st.session_state[code_key],
            language="python",
            theme="tomorrow_night",
            min_lines=12,
            max_lines=28,
            key=f"{code_key}_editor",
        )
        if code is not None:
            st.session_state[code_key] = code
    else:
        st.text_area("Python code", key=code_key, height=360)

    test_code = str(milestone.get("test_code") or "").strip()
    if test_code:
        with st.expander("Assert checks", expanded=False):
            st.code(test_code, language="python")
    else:
        st.caption("No assert checks for this milestone. Run code, inspect output, then mark done manually.")

    button_cols = st.columns(3)
    if button_cols[0].button("▶ Run milestone", key=f"{code_key}_run", use_container_width=True):
        solution_code = str(st.session_state.get(code_key, ""))
        script = build_mentor_task_script(solution_code, test_code)
        loading_slot = st.empty()
        with st.spinner("Running in the existing Jupyter kernel..."):
            loading_slot.markdown(
                """
<div class="skeleton console-card">
    <div class="sk" style="width: 42%"></div>
    <div class="sk" style="width: 76%"></div>
    <div class="sk" style="width: 58%"></div>
</div>
                """,
                unsafe_allow_html=True,
            )
            result = run_code_in_notebook_kernel_sync(script)
        loading_slot.empty()
        classification = classify_task_result(result)
        updates: dict[str, Any] = {
            "solution_code": solution_code,
            "last_result": result,
            "last_classification": classification,
        }
        if test_code and classification == "PASS":
            updates["done"] = True
        set_data_lab_milestone_updates(project_id, milestone_id, updates)
        st.session_state[result_key] = result

    if button_cols[1].button("Save code", key=f"{code_key}_save", use_container_width=True):
        set_data_lab_milestone_updates(project_id, milestone_id, {"solution_code": st.session_state.get(code_key, "")})
        st.success("Milestone code saved.")

    if button_cols[2].button("Reset code", key=f"{code_key}_reset", use_container_width=True):
        st.session_state[code_key] = starter_code
        set_data_lab_milestone_updates(project_id, milestone_id, {"solution_code": starter_code})
        st.rerun()

    result = st.session_state.get(result_key) or record.get("last_result")
    if isinstance(result, dict) and result:
        render_project_milestone_result(result)


def render_project_checklist(project: dict[str, Any], milestone: dict[str, Any], record: dict[str, Any]) -> None:
    checklist = list(milestone.get("checklist", []))
    if milestone.get("type") == "visualization":
        for item in milestone.get("quality_checklist", []):
            if item not in checklist:
                checklist.append(item)
    if not checklist:
        return

    raw_checked_items = record.get("checked_items", [])
    checked_items = {str(item) for item in raw_checked_items} if isinstance(raw_checked_items, list) else set()
    stats = checklist_progress(checklist, checked_items)
    st.markdown("##### Checklist")
    st.caption(f"{stats['done']}/{stats['total']} checked")
    for index, item in enumerate(checklist):
        item_key = project_milestone_widget_key(project["id"], milestone["id"], f"check_{index}")
        previous = item in checked_items
        current = st.checkbox(str(item), value=previous, key=item_key)
        if current != previous:
            set_data_lab_milestone_checklist_item(project["id"], milestone["id"], str(item), current)
            st.rerun()


def render_project_writing_milestone(project: dict[str, Any], milestone: dict[str, Any], record: dict[str, Any]) -> None:
    prompt = str(milestone.get("reflection_prompt") or milestone.get("description") or "").strip()
    if prompt:
        st.markdown("##### Writing prompt")
        st.markdown(prompt)

    notes_key = project_milestone_widget_key(project["id"], milestone["id"], "notes")
    if notes_key not in st.session_state:
        st.session_state[notes_key] = str(record.get("notes") or "")
    st.text_area("Notes / reflection", key=notes_key, height=180)
    if st.button("Save notes", key=f"{notes_key}_save", use_container_width=True):
        set_data_lab_milestone_updates(project["id"], milestone["id"], {"notes": st.session_state.get(notes_key, "")})
        st.success("Notes saved.")


def render_data_lab_milestone(project: dict[str, Any], milestone: dict[str, Any]) -> None:
    project_id = project["id"]
    milestone_id = milestone["id"]
    done = is_data_lab_milestone_done(project_id, milestone_id)
    record = get_data_lab_milestone_record(project_id, milestone_id)
    icon = "✅" if done else "□"
    required_label = "required" if milestone.get("required", True) else "optional"
    with st.expander(f"{icon} {milestone['title']} · {milestone['type']} · {required_label}", expanded=not done):
        st.markdown(milestone["description"])
        hints = milestone.get("dataset_hints", [])
        if hints:
            st.caption("Dataset hints: " + " · ".join(str(item) for item in hints))

        milestone_type = str(milestone.get("type") or "")
        if milestone_type in {"code", "visualization"}:
            render_project_code_runner(project, milestone, record)
        if milestone_type in {"reflection", "report", "model_card"}:
            render_project_writing_milestone(project, milestone, record)
        render_project_checklist(project, milestone, record)

        portfolio_output = str(milestone.get("portfolio_output") or "").strip()
        if portfolio_output:
            st.markdown("##### Portfolio output")
            st.markdown(portfolio_output)

        button_cols = st.columns(2)
        if done:
            button_cols[0].button(
                "Сбросить milestone",
                key=f"data_lab_reset_{project_id}_{milestone_id}",
                on_click=set_data_lab_milestone_done,
                args=(project_id, milestone_id, False),
                use_container_width=True,
            )
        else:
            button_cols[0].button(
                "Отметить готово",
                key=f"data_lab_done_{project_id}_{milestone_id}",
                on_click=set_data_lab_milestone_done,
                args=(project_id, milestone_id, True),
                use_container_width=True,
            )


def render_data_lab_before_start(
    project: dict[str, Any],
    *,
    note_index: dict[str, Any],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
    datasets: list[dict[str, Any]],
) -> None:
    checks = project_readiness_checks(
        project,
        note_index=note_index,
        practice_cards=practice_cards,
        mentor_tasks=mentor_tasks,
        datasets=datasets,
    )
    readiness = calculate_readiness(checks)

    st.markdown("#### Before you start")
    st.markdown(
        f"{render_readiness_badge(readiness)} "
        f"<span class='muted-small'>{readiness['done']}/{readiness['total']} prerequisites completed</span>",
        unsafe_allow_html=True,
    )
    if readiness["missing"]:
        with st.expander("Missing prerequisites", expanded=False):
            for item in readiness["missing"]:
                st.markdown(f"- {item}")

    if project.get("related_theory_paths"):
        st.markdown("##### Theory notes")
        theory_cols = st.columns(2)
        for index, theory_path in enumerate(project["related_theory_paths"]):
            note = note_from_relative_path(str(theory_path), note_index) or resolve_related_note(str(theory_path), note_index)
            col = theory_cols[index % len(theory_cols)]
            if note:
                label = f"📖 {Path(str(theory_path)).stem.replace('_', ' ')}"
                col.button(
                    label,
                    key=f"data_lab_theory_{project['id']}_{index}",
                    on_click=open_theory_note,
                    args=(note,),
                    use_container_width=True,
                )
            else:
                col.button(
                    f"{theory_path} — missing",
                    key=f"data_lab_theory_missing_{project['id']}_{index}",
                    disabled=True,
                    use_container_width=True,
                )

    if project.get("related_practice_ids"):
        st.markdown("##### Practice cards")
        for card_id in project["related_practice_ids"]:
            card = find_practice_card(str(card_id), practice_cards)
            if not card:
                st.button(f"{card_id} — missing", key=f"data_lab_practice_missing_{project['id']}_{card_id}", disabled=True)
                continue
            status = get_card_status(card)
            cols = st.columns([0.7, 0.3])
            cols[0].caption(f"{card['title']} · {card.get('section', '')} · {PRACTICE_META[status]['label']}")
            cols[1].button(
                "Open practice",
                key=f"data_lab_practice_{project['id']}_{card_id}",
                on_click=open_practice_card,
                args=(card["id"],),
                use_container_width=True,
            )

    if project.get("related_task_ids"):
        st.markdown("##### Mentor tasks")
        for task_ref in project["related_task_ids"]:
            matches = related_mentor_tasks(str(task_ref), mentor_tasks)
            task = matches[0] if matches else None
            cols = st.columns([0.7, 0.3])
            if task:
                done_count = sum(1 for item in matches if get_mentor_task_status(item["id"]) == STATUS_DONE)
                cols[0].caption(f"{task_ref}: {done_count}/{len(matches)} solved · first: {task['title']}")
                cols[1].button(
                    "Open task",
                    key=f"data_lab_task_{project['id']}_{task_ref}",
                    on_click=open_mentor_task,
                    args=(task,),
                    use_container_width=True,
                )
            else:
                cols[0].caption(f"{task_ref} — no matching task found")
                cols[1].button(
                    "Open task",
                    key=f"data_lab_task_missing_{project['id']}_{task_ref}",
                    disabled=True,
                    use_container_width=True,
                )

    dataset_names = project.get("related_dataset_names") or project.get("datasets", [])
    if dataset_names:
        st.markdown("##### Datasets to inspect")
        dataset_cols = st.columns(max(1, min(3, len(dataset_names))))
        for index, dataset_name in enumerate(dataset_names):
            col = dataset_cols[index % len(dataset_cols)]
            exists = find_dataset_record(str(dataset_name), datasets) is not None
            col.button(
                f"📊 {dataset_name}" if exists else f"{dataset_name} — missing",
                key=f"data_lab_before_dataset_{project['id']}_{dataset_name}",
                on_click=open_dataset_tab if exists else None,
                args=(dataset_name,) if exists else None,
                disabled=not exists,
                use_container_width=True,
            )


def render_data_lab_portfolio_output(project: dict[str, Any]) -> None:
    st.markdown("#### Portfolio output")
    templates = project.get("related_portfolio_templates", [])
    if templates:
        for template in templates:
            with st.expander(template["title"], expanded=False):
                if template.get("what_to_write"):
                    st.markdown("##### What to write")
                    st.markdown(template["what_to_write"])
                if template.get("chart_or_table"):
                    st.markdown("##### Chart/table to include")
                    st.markdown(template["chart_or_table"])
                if template.get("readme_bullet"):
                    st.markdown("##### README bullet")
                    st.markdown(template["readme_bullet"])
    st.markdown("##### Project prompt")
    st.markdown(project.get("portfolio_prompt") or "Write a concise project summary.")


def render_data_lab_project_completion(project: dict[str, Any], stats: dict[str, Any]) -> None:
    complete = is_data_lab_project_complete(project["id"])
    can_complete = bool(stats.get("complete"))
    st.markdown("#### Project completion")
    if complete:
        st.success("Project marked complete.")
        st.button(
            "Снять отметку complete",
            key=f"data_lab_project_uncomplete_{project['id']}",
            on_click=set_data_lab_project_complete,
            args=(project, False),
        )
    else:
        st.caption("Финальную отметку можно поставить только когда все required milestones закрыты.")
        missing = stats.get("missing_required", [])
        if missing:
            st.caption("Missing required: " + ", ".join(str(item) for item in missing))
        st.button(
            "Mark project complete",
            key=f"data_lab_project_complete_{project['id']}",
            on_click=set_data_lab_project_complete,
            args=(project, True),
            disabled=not can_complete,
        )


def render_project_workspace_scaffolder(project: dict[str, Any]) -> None:
    workspace_path = project_workspace_path(project, USER_PROJECTS_DIR)
    exists = workspace_path.exists()
    result_key = safe_widget_key("project_workspace_result", project["id"])

    st.markdown("#### Project Workspace")
    st.caption(
        "Creates a local user workspace under `user_projects/`. "
        "Datasets are not copied; generated files reference `../../datasets/...`."
    )
    st.code(str(workspace_path), language="text")

    overwrite = False
    if exists:
        st.warning("Workspace folder already exists. Existing files will not be overwritten unless you confirm.")
        overwrite = st.checkbox(
            "I understand this will overwrite generated workspace template files",
            key=safe_widget_key("project_workspace_overwrite", project["id"]),
        )

    if st.button(
        "Create project workspace",
        key=safe_widget_key("project_workspace_create", project["id"]),
        disabled=exists and not overwrite,
        use_container_width=True,
    ):
        result = create_project_workspace(
            project,
            USER_PROJECTS_DIR,
            PROJECT_ROOT,
            overwrite=overwrite,
        )
        st.session_state[result_key] = result

    result = st.session_state.get(result_key)
    if isinstance(result, dict):
        if result.get("created"):
            st.success(f"Workspace created: {result.get('path')}")
            with st.expander("Generated files", expanded=False):
                for item in result.get("written", []):
                    st.markdown(f"- `{item}`")
        elif result.get("exists"):
            st.info(f"Workspace already exists: {result.get('path')}")

    st.caption(
        "Open generated files manually in Finder/VS Code. Start with README.md, write findings in portfolio.md, "
        "and place charts/tables under artifacts/."
    )


def parse_experiment_metrics_from_state(project_id: str) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for metric_name in SUPPORTED_METRICS:
        value = st.session_state.get(safe_widget_key("experiment_metric", project_id, metric_name), "")
        text = str(value).strip()
        if not text:
            continue
        try:
            metrics[metric_name] = float(text)
        except ValueError:
            continue
    return metrics


def render_experiment_tracker(project: dict[str, Any]) -> None:
    if str(project.get("track") or "").casefold() != "classic ml":
        return

    workspace_path = project_workspace_path(project, USER_PROJECTS_DIR)
    records_path = experiment_records_path(workspace_path)
    records = load_experiment_records(records_path)
    summary = summarize_experiments(records)
    project_id = project["id"]

    st.markdown("#### Experiment Tracker Lite")
    st.caption(
        "Local JSONL log for ML runs. Save only metrics you actually produced in Notebook or entered manually. "
        "Raw datasets are never stored here."
    )
    st.code(str(records_path), language="text")

    metric_cols = st.columns(3)
    metric_cols[0].metric("Runs", summary["total"])
    metric_cols[1].metric("Completed", summary["by_status"].get("completed", 0))
    metric_cols[2].metric("Failed", summary["by_status"].get("failed", 0))

    with st.expander("Save current experiment summary", expanded=False):
        status = st.selectbox(
            "Status",
            ["draft", "completed", "failed"],
            key=safe_widget_key("experiment_status", project_id),
        )
        model_name = st.text_input(
            "Model name",
            value="LogisticRegression",
            key=safe_widget_key("experiment_model", project_id),
        )
        target_column = st.text_input(
            "Target column",
            value="converted",
            key=safe_widget_key("experiment_target", project_id),
        )
        feature_columns_text = st.text_area(
            "Feature columns (comma or newline separated)",
            key=safe_widget_key("experiment_features", project_id),
            height=80,
            placeholder="events_total, event_type__cart.shown, event_type__checkout.shown",
        )
        parameters_text = st.text_area(
            "Parameters JSON",
            key=safe_widget_key("experiment_parameters", project_id),
            height=90,
            placeholder='{"class_weight": "balanced", "max_iter": 1000}',
        )

        st.markdown("##### Metrics")
        metric_grid = st.columns(5)
        for index, metric_name in enumerate(SUPPORTED_METRICS):
            metric_grid[index % len(metric_grid)].text_input(
                metric_name,
                key=safe_widget_key("experiment_metric", project_id, metric_name),
                placeholder="empty",
            )

        notes = st.text_area(
            "Notes",
            key=safe_widget_key("experiment_notes", project_id),
            height=100,
            placeholder="What changed? What did the metric mean? Any leakage or data caveat?",
        )
        code_snippet = st.text_area(
            "Code snippet",
            key=safe_widget_key("experiment_code", project_id),
            height=140,
            placeholder="Paste the exact code snippet that produced these metrics.",
        )
        artifact_paths_text = st.text_area(
            "Artifact paths (comma or newline separated)",
            key=safe_widget_key("experiment_artifacts", project_id),
            height=70,
            placeholder="artifacts/tables/metrics.csv, artifacts/charts/confusion_matrix.png",
        )

        if st.button("Save experiment record", key=safe_widget_key("experiment_save", project_id), use_container_width=True):
            metrics = parse_experiment_metrics_from_state(project_id)
            record = {
                "project_id": project_id,
                "dataset_names": project.get("related_dataset_names") or project.get("datasets") or [],
                "target_column": target_column,
                "feature_columns": feature_columns_text,
                "model_name": model_name,
                "parameters": parameters_text,
                "metrics": metrics,
                "notes": notes,
                "code_snippet": code_snippet,
                "artifact_paths": artifact_paths_text,
                "status": status,
            }
            saved = save_experiment_record(record, records_path)
            st.success(f"Experiment saved: {saved['id']}")
            st.rerun()

    records = load_experiment_records(records_path)
    if not records:
        st.info("No experiment records yet. Run a milestone in Notebook, copy real metrics here, then save a record.")
        return

    metric_options = summarize_experiments(records)["metric_names"] or list(SUPPORTED_METRICS)
    selected_metric = st.selectbox(
        "Compare by metric",
        metric_options,
        key=safe_widget_key("experiment_compare_metric", project_id),
    )
    comparison = compare_experiments(records, selected_metric)
    st.dataframe(comparison, use_container_width=True, hide_index=True)

    with st.expander("Raw experiment records", expanded=False):
        st.json(records)


def render_data_lab_project_detail(
    project: dict[str, Any],
    datasets: list[dict[str, Any]],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
    note_index: dict[str, Any],
) -> None:
    stats = project_progress_from_record(project, get_data_lab_project_record(project["id"]))
    st.markdown(
        render_card(
            str(project["title"]),
            str(project["goal"]),
            eyebrow="Project detail",
            meta=f"{stats['done']}/{stats['total']} milestones · {project.get('estimated_time', '')}",
            status="PASS" if stats["total"] and stats["done"] == stats["total"] else "IN PROGRESS",
            content_html=render_metric_tile(
                "Milestone progress",
                stats["done"],
                total=stats["total"],
                progress=stats["ratio"],
                status="PASS" if stats["total"] and stats["done"] == stats["total"] else "IN PROGRESS",
            ),
        ),
        unsafe_allow_html=True,
    )

    detail_tiles = [
        render_metric_tile("Level", project.get("level", "—"), status="INFO"),
        render_metric_tile("Datasets", len(project.get("datasets", [])), status="INFO"),
        render_metric_tile("Skills", len(project.get("skills", [])), status="READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(detail_tiles)}</div>', unsafe_allow_html=True)

    render_section_eyebrow_block("Business Context")
    st.markdown(project.get("business_context") or "No business context provided.")

    render_data_lab_before_start(
        project,
        note_index=note_index,
        practice_cards=practice_cards,
        mentor_tasks=mentor_tasks,
        datasets=datasets,
    )

    render_section_eyebrow_block("Datasets")
    dataset_cols = st.columns(max(1, min(3, len(project.get("datasets", [])) or 1)))
    for index, dataset_name in enumerate(project.get("datasets", [])):
        col = dataset_cols[index % len(dataset_cols)]
        exists = find_dataset_record(dataset_name, datasets) is not None
        if exists:
            col.button(
                f"📊 {dataset_name}",
                key=f"data_lab_dataset_{project['id']}_{dataset_name}",
                on_click=open_dataset_tab,
                args=(dataset_name,),
                use_container_width=True,
            )
        else:
            col.button(
                f"{dataset_name} — missing",
                key=f"data_lab_dataset_{project['id']}_{dataset_name}",
                disabled=True,
                use_container_width=True,
            )

    if project.get("prerequisites"):
        render_section_eyebrow_block("Prerequisites")
        st.markdown("\n".join(f"- {item}" for item in project["prerequisites"]))

    render_section_eyebrow_block("Milestones")
    for milestone in project.get("milestones", []):
        render_data_lab_milestone(project, milestone)

    render_section_eyebrow_block("Deliverables")
    st.markdown("\n".join(f"- {item}" for item in project.get("deliverables", [])))

    render_data_lab_portfolio_output(project)
    render_project_workspace_scaffolder(project)
    render_experiment_tracker(project)
    render_data_lab_project_completion(project, stats)


def render_data_lab_projects_tab(
    projects: list[dict[str, Any]],
    datasets: list[dict[str, Any]],
    practice_cards: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
    note_index: dict[str, Any],
    *,
    title: str = "🧪 Data Lab Projects",
    description: str = "End-to-end проекты: от датасета и анализа до графиков, выводов и portfolio output. Код пока запускай в Notebook вручную.",
) -> None:
    st.markdown(
        render_card(
            title,
            description,
            eyebrow="Build cluster",
            status="READY" if projects else "TODO",
        ),
        unsafe_allow_html=True,
    )

    if not projects:
        st.markdown(
            render_card(
                "Project recipes не найдены",
                "Добавь JSON recipes under content/projects/, чтобы собрать Data Lab catalog.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return

    stats = data_lab_projects_progress(projects)
    milestone_ratio = stats["milestones_done"] / stats["milestones_total"] if stats["milestones_total"] else 0.0
    project_ratio = stats["projects_done"] / stats["projects_total"] if stats["projects_total"] else 0.0
    tiles = [
        render_metric_tile("Проектов", stats["projects_total"], status="INFO"),
        render_metric_tile(
            "Проекты готовы",
            stats["projects_done"],
            total=stats["projects_total"],
            progress=project_ratio,
            status="PASS" if project_ratio == 1 else "IN PROGRESS",
        ),
        render_metric_tile(
            "Milestones",
            stats["milestones_done"],
            total=stats["milestones_total"],
            progress=milestone_ratio,
            status="PASS" if milestone_ratio == 1 else "IN PROGRESS",
        ),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(tiles)}</div>', unsafe_allow_html=True)

    selected_id = st.session_state.get("selected_data_lab_project")
    if selected_id not in {project["id"] for project in projects}:
        selected_id = projects[0]["id"]
        st.session_state["selected_data_lab_project"] = selected_id

    list_col, detail_col = st.columns([0.38, 0.62])
    with list_col:
        render_section_eyebrow_block("Project Catalog")
        for project in projects:
            render_data_lab_project_card(project)

    selected_project = next(project for project in projects if project["id"] == selected_id)
    with detail_col:
        render_data_lab_project_detail(selected_project, datasets, practice_cards, mentor_tasks, note_index)


def render_experiments_tab(projects: list[dict[str, Any]]) -> None:
    st.markdown("### 🧪 Experiments")
    st.markdown(
        "Read-only log of local ML experiment records saved from project workspaces. "
        "No training runs here; save real metrics from ML Lab."
    )

    records = experiment_records_for_projects(projects)
    if not records:
        st.markdown(
            '<div class="empty-state-line">No experiment runs found. Open ML Lab and save a real experiment summary after a Notebook run.</div>',
            unsafe_allow_html=True,
        )
        st.button(
            "Open ML Lab",
            key="experiments_empty_open_ml_lab",
            on_click=open_tab,
            args=("🤖 ML Lab",),
        )
        return

    summary = summarize_experiments(records)
    metric_tiles = [
        render_metric_tile("Runs", summary["total"], status="INFO"),
        render_metric_tile("Completed", summary["by_status"].get("completed", 0), status="PASS"),
        render_metric_tile("Failed", summary["by_status"].get("failed", 0), status="FAIL"),
        render_metric_tile("Metrics tracked", len(summary["metric_names"]), meta=", ".join(summary["metric_names"][:3]), status="READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(metric_tiles)}</div>', unsafe_allow_html=True)

    metric_options = summary["metric_names"] or list(SUPPORTED_METRICS)
    selected_metric = st.selectbox("Compare by metric", metric_options, key="experiments_compare_metric")
    comparison = compare_experiments(records, selected_metric)
    st.dataframe(comparison, use_container_width=True, hide_index=True)

    rows = []
    for record in records:
        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        rows.append(
            {
                "timestamp": record.get("timestamp", ""),
                "project": record.get("project_title", record.get("project_id", "")),
                "status": record.get("status", ""),
                "model": record.get("model_name", ""),
                "metrics": json.dumps(metrics, ensure_ascii=False, sort_keys=True),
                "notes": record.get("notes", ""),
            }
        )
    st.markdown("#### Experiment records")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def artifact_markup(artifact: str) -> str:
    value = artifact.strip()
    if not value:
        return ""
    safe_value = html.escape(value)
    if value.startswith(("http://", "https://")):
        return f'<a href="{html.escape(value, quote=True)}" target="_blank" rel="noopener noreferrer">{safe_value}</a>'
    return safe_value


def render_portfolio_export_section(cards: list[dict[str, Any]], data_lab_projects: list[dict[str, Any]]) -> None:
    completed_projects = [project for project in data_lab_projects if is_data_lab_project_complete(project["id"])]
    completed_cards = [card for card in cards if get_card_status(card) == PRACTICE_DONE]
    project_by_id = {project["id"]: project for project in completed_projects}
    card_by_id = {card["id"]: card for card in completed_cards}

    render_section_eyebrow_block("Portfolio Export")
    st.markdown(
        render_card(
            "Markdown exporter",
            EXPORT_WARNING,
            eyebrow="Local artifact",
            status="NEEDS REVIEW",
        ),
        unsafe_allow_html=True,
    )

    if not completed_projects and not completed_cards:
        st.markdown(
            render_card(
                "Экспорт пока недоступен",
                "Заверши Data Lab проект или practice card, чтобы собрать markdown-шаблон.",
                eyebrow="Empty state",
                status="IN PROGRESS",
            ),
            unsafe_allow_html=True,
        )
        return

    selected_project_ids = st.multiselect(
        "Completed Data Lab projects",
        options=[project["id"] for project in completed_projects],
        format_func=lambda project_id: project_by_id[project_id]["title"],
        key="portfolio_export_projects",
    )
    selected_card_ids = st.multiselect(
        "Completed practice cards",
        options=[card["id"] for card in completed_cards],
        format_func=lambda card_id: card_by_id[card_id]["title"],
        key="portfolio_export_cards",
    )

    selected_projects = [project_by_id[project_id] for project_id in selected_project_ids]
    selected_cards = [card_by_id[card_id] for card_id in selected_card_ids]
    output_records = {card["id"]: get_output_record(card["id"]) for card in selected_cards}
    markdown = generate_portfolio_markdown(selected_projects, selected_cards, output_records)
    target_path = portfolio_export_path(PORTFOLIO_DIR)

    st.caption(f"Export target: {target_path}")
    with st.expander("Markdown preview", expanded=bool(selected_projects or selected_cards)):
        st.code(markdown, language="markdown")

    if st.button(
        "Export markdown",
        key="portfolio_export_write",
        disabled=not (selected_projects or selected_cards),
        use_container_width=True,
    ):
        try:
            PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
            target_path = portfolio_export_path(PORTFOLIO_DIR)
            target_path.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            st.error(f"Не удалось записать portfolio markdown: {exc}")
        else:
            st.success(f"Portfolio markdown exported: {target_path}")


def render_portfolio_tab(cards: list[dict[str, Any]], data_lab_projects: list[dict[str, Any]]) -> None:
    st.markdown(
        render_card(
            "📁 Portfolio",
            "Здесь собираются результаты практики: артефакты, выводы и следы работы, которые потом можно превращать в резюме и GitHub.",
            eyebrow="Output cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    if not cards and not data_lab_projects:
        st.markdown(
            render_card(
                "Портфолио пустое",
                "Открой Practice или Data Lab и сохрани первый output.",
                eyebrow="Empty state",
                status="IN PROGRESS",
            ),
            unsafe_allow_html=True,
        )
        return

    practice_stats = practice_progress(cards)
    output_stats = portfolio_progress(cards)
    output_ratio = output_stats["with_outputs"] / output_stats["total"] if output_stats["total"] else 0.0
    practice_total = practice_stats["total"]
    practice_done = practice_stats[PRACTICE_DONE]
    practice_ratio = practice_done / practice_total if practice_total else 0.0
    portfolio_tiles = [
        render_metric_tile("Output записан", output_stats["with_outputs"], total=output_stats["total"], progress=output_ratio, status="PASS" if output_ratio == 1 and output_stats["total"] else "IN PROGRESS"),
        render_metric_tile("Практика сделана", practice_done, total=practice_total, progress=practice_ratio, status="PASS" if practice_ratio == 1 and practice_total else "IN PROGRESS"),
        render_metric_tile("Без output", output_stats["missing"], status="NEEDS REVIEW" if output_stats["missing"] else "READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(portfolio_tiles)}</div>', unsafe_allow_html=True)

    render_portfolio_export_section(cards, data_lab_projects)

    render_section_eyebrow_block("Artifacts")
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
        st.markdown(
            render_card(
                "По фильтру ничего нет",
                "Смени фильтр или добавь output в карточке практики.",
                eyebrow="Empty state",
                status="READY",
            ),
            unsafe_allow_html=True,
        )
        return

    for card in filtered:
        record = get_output_record(card["id"])
        has_output = output_has_content(record)
        summary = str(record.get("summary", "")).strip()
        artifact = str(record.get("artifact", "")).strip()
        reflection = str(record.get("reflection", "")).strip()
        updated_at = str(record.get("updated_at", "")).strip()

        output_status = "DONE" if has_output else "IN PROGRESS"
        card_meta = f"{card['section']} · {card['difficulty']} · {card['est_time']}"

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
                render_card(
                    card["title"],
                    card_meta,
                    eyebrow="Portfolio artifact",
                    status=output_status,
                    content_html=(
                        f'{render_status_chip(practice_status_to_chip(get_card_status(card)))} '
                        f'{render_status_chip(output_status)}'
                        '<div class="practice-output">' + "<br>".join(details) + "</div>"
                    ),
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                render_card(
                    card["title"],
                    "Открой карточку и заполни output, когда появится результат.",
                    eyebrow="Portfolio artifact",
                    meta=card_meta,
                    status=output_status,
                    content_html=(
                        f'{render_status_chip(practice_status_to_chip(get_card_status(card)))} '
                        f'{render_status_chip(output_status)}'
                    ),
                ),
                unsafe_allow_html=True,
            )

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
        chip = "ERROR"
        title = "Таймаут"
        message = f"Процесс остановлен после {elapsed:.2f} сек."
    elif result.get("exit_code") == 0:
        chip = "PASS"
        title = "Тесты прошли"
        message = f"Все встроенные assert-проверки прошли за {elapsed:.2f} сек."
    else:
        chip = "FAIL"
        title = "Тесты упали"
        message = f"Exit code: {result.get('exit_code')}"
    st.markdown(
        render_card(
            title,
            message,
            eyebrow="Run result",
            status=chip,
            extra_class="run-result",
        ),
        unsafe_allow_html=True,
    )
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


def extract_algorithm_tests_preview(code: str) -> str:
    match = re.search(r"def\s+run_tests\s*\([^)]*\):(?P<body>.*?)(?:\nif\s+__name__|$)", code or "", flags=re.S)
    if not match:
        return ""
    return "def run_tests():" + match.group("body").rstrip()


def render_timed_mock_controls(scope: str, item_id: str) -> int:
    cols = st.columns([0.35, 0.25, 0.4])
    limit = cols[0].selectbox(
        "Time limit",
        [10, 20, 30, 45],
        key=safe_widget_key("mock_limit", scope, item_id),
    )
    start_key = safe_widget_key("mock_start", scope, item_id)
    if cols[1].button("Start timer", key=f"{start_key}_button", use_container_width=True):
        st.session_state[start_key] = time.time()
    started_at = st.session_state.get(start_key)
    elapsed_minutes = 0
    if isinstance(started_at, (int, float)):
        elapsed_minutes = int((time.time() - started_at) // 60)
        cols[2].metric("Elapsed", f"{elapsed_minutes} min", delta=f"limit {limit} min")
    else:
        cols[2].caption("Timer not started. This is a lightweight elapsed-time display.")
    return elapsed_minutes


def render_algorithm_self_review(lesson: dict[str, Any], mode: str, last_result: dict[str, Any] | None = None) -> None:
    lesson_id = lesson["id"]
    st.markdown("#### Self-review")
    tests_passed_default = bool(last_result and last_result.get("exit_code") == 0 and not last_result.get("timed_out"))
    cols = st.columns(3)
    tests_passed = cols[0].checkbox(
        "Did solution pass tests?",
        value=tests_passed_default,
        key=safe_widget_key("algo_review_tests", lesson_id, mode),
    )
    time_spent = cols[1].number_input(
        "Time spent (min)",
        min_value=0,
        max_value=240,
        value=0,
        key=safe_widget_key("algo_review_time", lesson_id, mode),
    )
    retry_later = cols[2].checkbox(
        "Retry later",
        key=safe_widget_key("algo_review_retry", lesson_id, mode),
    )
    big_o = st.text_area(
        "Big O explanation",
        key=safe_widget_key("algo_review_big_o", lesson_id, mode),
        height=80,
        placeholder="Time: O(...), Space: O(...). Explain why.",
    )
    edge_cases = st.text_area(
        "Edge cases considered",
        key=safe_widget_key("algo_review_edges", lesson_id, mode),
        height=80,
        placeholder="empty input, duplicates, negative numbers, single element...",
    )
    hard = st.text_area(
        "What was hard?",
        key=safe_widget_key("algo_review_hard", lesson_id, mode),
        height=80,
    )
    if st.button("Save algorithm attempt", key=safe_widget_key("algo_review_save", lesson_id, mode), use_container_width=True):
        save_algorithm_attempt(
            lesson_id,
            {
                "mode": mode,
                "tests_passed": tests_passed,
                "time_spent_minutes": time_spent,
                "big_o_explanation": big_o,
                "edge_cases": edge_cases,
                "what_was_hard": hard,
                "retry_later": retry_later,
            },
        )
        st.success("Algorithm attempt saved.")


def render_algorithm_attempt_review(lesson: dict[str, Any]) -> None:
    attempts = get_algorithm_attempts(lesson["id"])
    render_section_eyebrow_block("Saved attempts")
    if not attempts:
        st.markdown(
            render_card(
                "Попыток пока нет",
                "Сохрани self-review после Practice или Timed Mock, чтобы видеть историю.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return
    st.dataframe(
        [
            {
                "timestamp": attempt.get("timestamp"),
                "mode": attempt.get("mode"),
                "tests_passed": attempt.get("tests_passed"),
                "time_spent_minutes": attempt.get("time_spent_minutes"),
                "retry_later": attempt.get("retry_later"),
                "big_o": attempt.get("big_o_explanation"),
            }
            for attempt in attempts
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_algorithms_tab(lessons: list[dict[str, Any]]) -> None:
    st.markdown(
        render_card(
            "🧩 Algorithms Lab",
            "Livecoding-тренажер по файлам ментора: теория из docstring, эталонный код и запуск встроенных assert-тестов.",
            eyebrow="Train cluster",
            status="READY" if lessons else "TODO",
        ),
        unsafe_allow_html=True,
    )

    if not lessons:
        st.markdown(
            render_card(
                "Алгоритмы не найдены",
                "Проверь папку content/source/vkat/VKAT-main/algos_patterns.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return

    stats = algorithm_progress(lessons)
    done_ratio = stats["done"] / stats["total"] if stats["total"] else 0.0
    metric_tiles = [
        render_metric_tile("Уроков", stats["total"], status="INFO"),
        render_metric_tile(
            "Пройдено",
            stats["done"],
            total=stats["total"],
            progress=done_ratio,
            status="PASS" if done_ratio == 1 else "IN PROGRESS",
        ),
        render_metric_tile("Осталось", stats["todo"], status="TODO" if stats["todo"] else "READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(metric_tiles)}</div>', unsafe_allow_html=True)

    mode = st.radio(
        "Mode",
        PRACTICE_MODES,
        key="algorithm_practice_mode",
        horizontal=True,
    )

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
    lesson_text = "\n".join([str(lesson.get("docstring") or ""), str(lesson.get("code") or "")])
    difficulty = infer_difficulty(lesson_text)
    expected_complexity = extract_expected_complexity(lesson_text)

    st.markdown(
        render_card(
            str(lesson["title"]),
            f"{lesson['id']} · difficulty: {difficulty} · expected: {expected_complexity}",
            eyebrow="Selected pattern",
            status=note_status_to_chip(status),
        ),
        unsafe_allow_html=True,
    )

    if lesson.get("error"):
        st.warning(f"Файл не удалось прочитать: {lesson['error']}")
        return

    if mode == "Timed Mock":
        render_timed_mock_controls("algorithm", lesson["id"])

    render_section_eyebrow_block("Теория")
    docstring = str(lesson.get("docstring") or "").strip()
    if docstring:
        st.markdown(f"```text\n{docstring}\n```")
    else:
        st.markdown(
            render_card(
                "Docstring не найден",
                "Открой эталонный код ниже и используй README/комментарии файла как источник.",
                eyebrow="Empty state",
                status="WEAK",
            ),
            unsafe_allow_html=True,
        )

    with st.expander("Эталонный код", expanded=False):
        st.code(str(lesson.get("code") or ""), language="python")

    if mode in {"Practice", "Timed Mock"}:
        render_section_eyebrow_block("Practice Setup")
        st.caption("Starter code: use the lesson templates/functions as your starting point. Run built-in tests when ready.")
        st.code(str(lesson.get("code") or ""), language="python")
        tests_preview = extract_algorithm_tests_preview(str(lesson.get("code") or ""))
        if tests_preview:
            with st.expander("Tests preview", expanded=False):
                st.code(tests_preview, language="python")
        render_section_eyebrow_block("Edge case checklist")
        for item in ["empty input", "single element", "duplicates", "negative values", "already sorted / reverse sorted"]:
            st.checkbox(item, key=safe_widget_key("algo_edge", lesson["id"], mode, item))
        st.text_area(
            "Explanation prompt",
            value="Explain the pattern, why the data structure fits, and the final time/space complexity.",
            key=safe_widget_key("algo_explanation_prompt", lesson["id"], mode),
            height=80,
        )

    result_key = f"algorithm_result_{lesson['id']}"
    if st.button("▶ Прогнать тесты", key=f"run_algorithm_{lesson['id']}", use_container_width=True):
        with st.spinner("Запускаю файл и встроенные assert-проверки..."):
            result = run_algorithm_tests(lesson["path"])
        st.session_state[result_key] = result
        if result.get("exit_code") == 0 and not result.get("timed_out"):
            set_algorithm_status(lesson["id"], STATUS_DONE, result)

    if result_key in st.session_state:
        render_algorithm_result(st.session_state[result_key])

    if mode in {"Practice", "Timed Mock"}:
        render_algorithm_self_review(lesson, mode, st.session_state.get(result_key))
    elif mode == "Review":
        render_algorithm_attempt_review(lesson)


def select_mentor_task(task_id: str) -> None:
    st.session_state["selected_mentor_task"] = task_id


def mentor_task_badge(task: dict[str, Any]) -> str:
    status = get_mentor_task_status(task["id"])
    confidence = str(task["confidence"])
    confidence_label = "требует ревью" if confidence == "low" else confidence
    return f"{render_status_chip(note_status_to_chip(status))} {render_status_chip('NEEDS REVIEW' if confidence == 'low' else 'READY')} <span class='muted-small'>{html.escape(confidence_label)}</span>"


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
    message_by_class = {
        "PASS": "Все assert-проверки прошли.",
        "FAIL": "Код запустился, но ожидаемые значения не совпали с assert-проверками.",
        "ERROR": "Код упал до прохождения проверок. Исправьте runtime-ошибку и запустите снова.",
        "TIMEOUT": "Выполнение заняло слишком много времени и было прервано.",
        "KERNEL_BUSY": "Jupyter-ядро уже выполняет другую ячейку или задачу.",
    }
    chip = classification if classification in {"PASS", "FAIL", "ERROR"} else ("ERROR" if classification == "TIMEOUT" else "BLOCKED")
    st.markdown(
        render_card(
            f"{classification or 'UNKNOWN'} · {elapsed:.2f}s",
            message_by_class.get(classification, "Проверь вывод и traceback ниже."),
            eyebrow="Task result",
            status=chip,
            extra_class="run-result",
        ),
        unsafe_allow_html=True,
    )

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


def render_kernel_panel_header(label: str = "python · kernel") -> None:
    kernel_status = notebook_kernel_status_label()
    st.markdown(
        f"""
<div class="console-panel">
    <div class="phead"><span class="dot3"><i></i><i></i><i></i></span><span>{html.escape(label)} {html.escape(kernel_status)}</span></div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_kernel_loading_skeleton(slot: Any) -> None:
    slot.markdown(
        """
<div class="skeleton console-card">
    <div class="sk" style="width: 38%"></div>
    <div class="sk" style="width: 82%"></div>
    <div class="sk" style="width: 64%"></div>
</div>
        """,
        unsafe_allow_html=True,
    )


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
        render_kernel_panel_header("python · kernel")
        render_section_eyebrow_block("Решение")
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
            loading_slot = st.empty()
            with st.spinner("Запускаю в Jupyter-ядре и проверяю assert..."):
                render_kernel_loading_skeleton(loading_slot)
                result = run_code_in_notebook_kernel_sync(final_script)
            loading_slot.empty()
            st.session_state[result_key] = result
            if classify_task_result(result) == "PASS":
                set_mentor_task_status(task["id"], STATUS_DONE, result)

        if button_cols[1].button("Сбросить код", key=f"reset_mentor_task_{task['id']}", use_container_width=True):
            st.session_state[code_key] = task["solution_starter"]
            st.rerun()

        if result_key in st.session_state:
            render_mentor_task_result(st.session_state[result_key])


def render_tasks_tab(mentor_data: dict[str, Any]) -> None:
    st.markdown(
        render_card(
            "🎯 Tasks",
            "Автопроверяемые задачи из ноутбуков ментора. В работу берутся только задания с `assert`.",
            eyebrow="Train cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    tasks = mentor_data.get("tasks", [])
    if not tasks:
        st.markdown(
            render_card(
                "Автозадачи не найдены",
                "Файл content/extracted/mentor_tasks.json отсутствует или не содержит checkable tasks.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return

    normal_tasks = [task for task in tasks if task["confidence"] in {"high", "medium"}]
    review_tasks = [task for task in tasks if task["confidence"] == "low"]
    stats = mentor_tasks_progress(tasks)
    solved_ratio = stats["done"] / stats["total"] if stats["total"] else 0.0
    metric_tiles = [
        render_metric_tile("Автозадач", len(tasks), status="INFO"),
        render_metric_tile("В работе", len(normal_tasks), status="IN PROGRESS"),
        render_metric_tile("Решено", stats["done"], total=stats["total"], progress=solved_ratio, status="PASS" if solved_ratio == 1 else "IN PROGRESS"),
        render_metric_tile("На ревью", len(review_tasks), status="NEEDS REVIEW" if review_tasks else "READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(metric_tiles)}</div>', unsafe_allow_html=True)

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
        st.markdown(
            render_card(
                "По этим фильтрам задач нет",
                "Смени notebook/confidence или открой секцию low-confidence ниже.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
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


def render_interview_question_practice(
    company: str,
    kind: str,
    index: int,
    text: str,
    mode: str,
) -> None:
    question_id = interview_question_id(company, kind, index, text)
    attempts = get_interview_attempts(question_id)
    repeat_label = " · repeat later" if attempts and attempts[-1].get("repeat_later") else ""
    latest_rating = attempts[-1].get("self_rating", 0) if attempts else 0
    card_status = "WEAK" if attempts and attempts[-1].get("repeat_later") else ("READY" if attempts else "TODO")
    st.markdown(
        render_card(
            f"{index}. {text}",
            f"{company} · {kind}",
            eyebrow="Interview prompt",
            meta=f"rating: {latest_rating}/5 · attempts: {len(attempts)}{repeat_label}" if attempts else "No attempts saved yet.",
            status=card_status,
        ),
        unsafe_allow_html=True,
    )
    if attempts:
        latest = attempts[-1]
        st.caption(
            f"Last rating: {latest.get('self_rating', 0)}/5 · attempts: {len(attempts)}{repeat_label}"
        )

    if mode in {"Practice", "Timed Mock"}:
        notes = st.text_area(
            "Answer notes",
            key=safe_widget_key("interview_notes", question_id, mode),
            height=90,
            placeholder="Write your answer in your own words. No ideal answer is generated here.",
        )
        cols = st.columns(3)
        rating = cols[0].slider(
            "Self-rating",
            1,
            5,
            3,
            key=safe_widget_key("interview_rating", question_id, mode),
        )
        repeat_later = cols[1].checkbox(
            "Repeat later",
            key=safe_widget_key("interview_repeat", question_id, mode),
        )
        if cols[2].button("Save answer", key=safe_widget_key("interview_save", question_id, mode), use_container_width=True):
            save_interview_attempt(
                question_id,
                {
                    "company": company,
                    "question": text,
                    "answer_notes": notes,
                    "self_rating": rating,
                    "repeat_later": repeat_later,
                },
            )
            st.success("Interview answer attempt saved.")
    elif mode == "Review" and attempts:
        with st.expander("Saved attempts", expanded=False):
            st.dataframe(
                [
                    {
                        "timestamp": attempt.get("timestamp"),
                        "rating": attempt.get("self_rating"),
                        "repeat_later": attempt.get("repeat_later"),
                        "notes": attempt.get("answer_notes"),
                    }
                    for attempt in attempts
                ],
                use_container_width=True,
                hide_index=True,
            )
    elif mode == "Review":
        st.markdown(
            render_card(
                "Попыток пока нет",
                "Ответь на вопрос в Practice или Timed Mock, чтобы он появился в Review.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )


def render_interviews_tab(interview_data: dict[str, Any]) -> None:
    st.markdown(
        render_card(
            "🎤 Interviews",
            "Вопросы и задачи с ML/DS собеседований, сгруппированные по компаниям.",
            eyebrow="Train cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    companies = interview_data.get("companies", [])
    if not companies:
        st.markdown(
            render_card(
                "Вопросы не найдены",
                "Проверь content/interview_questions/ml_ds_interview_questions.json.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
        return

    arena_stats = interview_arena_progress_summary()
    metric_tiles = [
        render_metric_tile("Компаний", interview_data.get("total_companies", len(companies)), status="INFO"),
        render_metric_tile("Вопросов", interview_data.get("total_questions", 0), status="INFO"),
        render_metric_tile("Задач", interview_data.get("total_tasks", 0), status="INFO"),
        render_metric_tile("Repeat later", arena_stats["questions_repeat_later"], status="WEAK" if arena_stats["questions_repeat_later"] else "READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(metric_tiles)}</div>', unsafe_allow_html=True)

    mode = st.radio(
        "Mode",
        PRACTICE_MODES,
        key="interview_practice_mode",
        horizontal=True,
    )
    if mode == "Timed Mock":
        render_timed_mock_controls("interview", "global")

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
        st.markdown(
            render_card(
                "По такому фильтру вопросов нет",
                "Очисти поиск или выбери другую компанию.",
                eyebrow="Empty state",
                status="TODO",
            ),
            unsafe_allow_html=True,
        )
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
                st.markdown(render_status_chip("READY") + f" <span class='muted-small'>Актуальность: {html.escape(str(relevance))}</span>", unsafe_allow_html=True)
            if questions:
                render_section_eyebrow_block("Вопросы")
                for index, question in enumerate(questions, start=1):
                    render_interview_question_practice(entry["company"], "question", index, question, mode)
            if tasks:
                render_section_eyebrow_block("Задачи")
                for index, task in enumerate(tasks, start=1):
                    render_interview_question_practice(entry["company"], "task", index, task, mode)
            if entry.get("notes"):
                render_section_eyebrow_block("Дополнительно")
                for note in entry["notes"]:
                    st.markdown(f"- {note}")


def render_architecture_tab(architecture_data: dict[str, Any]) -> None:
    st.markdown(
        render_card(
            "🏗 Architecture",
            "Отдельный учебный справочник по архитектурным принципам и trade-offs.",
            eyebrow="Output cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    document_html = str(architecture_data.get("html") or "")
    sections = architecture_data.get("sections", [])
    if not document_html:
        st.markdown(
            render_card(
                "Материал по архитектуре не найден",
                "Проверь content/ или открой README, если справочник ещё не добавлен.",
                eyebrow="Empty state",
                status="NEEDS REVIEW",
            ),
            unsafe_allow_html=True,
        )
        return

    architecture_tiles = [
        render_metric_tile("Документ", architecture_data.get("title", "Architecture"), status="READY"),
        render_metric_tile("Разделов", len(sections), status="INFO"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(architecture_tiles)}</div>', unsafe_allow_html=True)

    section_titles = ["Весь документ"] + [section["title"] for section in sections]
    control_cols = st.columns([0.5, 0.5])
    selected_title = control_cols[0].selectbox("Раздел", section_titles, key="architecture_section")
    query = control_cols[1].text_input("Поиск по названиям разделов", key="architecture_search").strip().casefold()

    if query:
        matches = [section for section in sections if query in section["title"].casefold()]
        if matches:
            st.caption("Найденные разделы: " + " · ".join(section["title"] for section in matches[:8]))
        else:
            st.markdown(
                render_card(
                    "Разделы не найдены",
                    "Очисти поиск или попробуй другое слово.",
                    eyebrow="Empty state",
                    status="READY",
                ),
                unsafe_allow_html=True,
            )

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
    render_section_eyebrow_block("Document")
    st.markdown(
        f'<div class="console-card run-result"><div class="architecture-doc">{html_to_render}</div></div>',
        unsafe_allow_html=True,
    )


def note_from_relative_path(relative_path: str, note_index: dict[str, Any]) -> dict[str, str] | None:
    wanted = str(relative_path or "").strip().casefold()
    if not wanted:
        return None
    for note in note_index.get("all_notes", []):
        if str(note.get("relative_path", "")).casefold() == wanted:
            return note
    return None


def render_theory_quality_tab(note_index: dict[str, Any]) -> None:
    st.markdown(
        render_card(
            "🧭 Theory Quality",
            "Read-only срез качества базы знаний. Он использует готовые отчёты и не сканирует vault автоматически.",
            eyebrow="Learn cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
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
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/check_content_gate.py --reaudit --vault "$VAULT_PATH"
```

Если `VAULT_PATH` не задан, подставь абсолютный путь к Obsidian vault через `--vault`.
            """
        )

    if not audit_report:
        st.markdown(
            render_card(
                "Theory audit report не найден",
                f"Запусти аудит вручную. Ожидаемый файл: {THEORY_AUDIT_REPORT_PATH}",
                eyebrow="Empty state",
                status="NEEDS REVIEW",
            ),
            unsafe_allow_html=True,
        )
        return

    average_score = audit_summary.get("average_quality_score", "—")
    try:
        quality_progress = float(average_score) / 100
    except (TypeError, ValueError):
        quality_progress = None
    meta_tiles = [
        render_metric_tile("Заметок", audit_summary.get("total_notes", 0), status="INFO"),
        render_metric_tile("Средний score", average_score, total=100, progress=quality_progress, status="PASS" if quality_progress and quality_progress >= 0.7 else "WEAK"),
        render_metric_tile("Без examples", len(audit_summary.get("notes_without_examples", []) or []), status="NEEDS REVIEW"),
        render_metric_tile("Без sources", len(audit_summary.get("notes_without_sources", []) or []), status="NEEDS REVIEW"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(meta_tiles)}</div>', unsafe_allow_html=True)

    if audit_summary.get("generated_at"):
        st.caption(f"Theory audit generated: {audit_summary['generated_at']}")
    if audit_report.get("vault"):
        st.caption(f"Vault: {audit_report['vault']}")

    render_section_eyebrow_block("Weakest Notes")
    weak = weakest_notes(audit_report, limit=20)
    if not weak:
        st.markdown(render_card("Weakest notes не найдены", "В текущем отчёте нет списка слабых заметок.", eyebrow="Empty state", status="READY"), unsafe_allow_html=True)
    else:
        for index, note in enumerate(weak):
            relative_path = str(note.get("relative_path") or "")
            title = str(note.get("title") or relative_path)
            score = note.get("quality_score", "—")
            words = note.get("word_count", "—")
            section = str(note.get("section") or "")
            try:
                score_number = int(score)
            except (TypeError, ValueError):
                score_number = 0
            st.markdown(
                f"""
<div class="health-row {'health-row-pass' if score_number >= 70 else 'health-row-fail'}">
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
        render_section_eyebrow_block("Notes Without Examples")
        examples_missing = report_list(audit_summary, "notes_without_examples", limit=30)
        if examples_missing:
            st.markdown("\n".join(f"- `{path}`" for path in examples_missing))
        else:
            st.markdown(render_card("Examples закрыты", "Все заметки имеют examples по текущей эвристике.", eyebrow="Audit", status="PASS"), unsafe_allow_html=True)

    with list_cols[1]:
        render_section_eyebrow_block("Notes Without Sources")
        sources_missing = report_list(audit_summary, "notes_without_sources", limit=30)
        if sources_missing:
            st.markdown("\n".join(f"- `{path}`" for path in sources_missing))
        else:
            st.markdown(render_card("Sources закрыты", "Все заметки имеют sources по текущей эвристике.", eyebrow="Audit", status="PASS"), unsafe_allow_html=True)

    render_section_eyebrow_block("Coverage")
    if not coverage_report:
        st.markdown(render_card("Coverage report не найден", f"Ожидаемый файл: {COVERAGE_REPORT_PATH}", eyebrow="Empty state", status="NEEDS REVIEW"), unsafe_allow_html=True)
        return

    if cov_summary.get("generated_at"):
        st.caption(f"Coverage report generated: {cov_summary['generated_at']}")

    missing = missing_required_topics(coverage_report)
    if missing:
        render_section_eyebrow_block("Missing Required Topics")
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
        st.markdown(render_card("Required topics закрыты", "Missing required topics не найдены в coverage report.", eyebrow="Coverage", status="PASS"), unsafe_allow_html=True)

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
        render_section_eyebrow_block("Coverage By Track")
        st.dataframe(track_rows, use_container_width=True, hide_index=True)

    render_section_eyebrow_block("Content Quality Gate")
    gate_report = load_json_report(CONTENT_GATE_REPORT_PATH)
    if not gate_report:
        st.markdown(render_card("Content gate report не найден", "Запусти tools/check_content_gate.py --reaudit вручную.", eyebrow="Empty state", status="NEEDS REVIEW"), unsafe_allow_html=True)
        return

    gate_summary = gate_report.get("summary") if isinstance(gate_report.get("summary"), dict) else {}
    gate_tiles = [
        render_metric_tile("Gate PASS", gate_summary.get("passed_topics", 0), status="PASS"),
        render_metric_tile("Gate FAIL", gate_summary.get("failed_topics", 0), status="FAIL" if gate_summary.get("failed_topics", 0) else "READY"),
        render_metric_tile("Required failed", len(gate_summary.get("failed_required_topic_ids", []) or []), status="FAIL" if gate_summary.get("failed_required_topic_ids") else "READY"),
        render_metric_tile("Threshold", gate_report.get("threshold", "—"), status="INFO"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(gate_tiles)}</div>', unsafe_allow_html=True)
    if gate_report.get("generated_at"):
        st.caption(f"Content gate generated: {gate_report['generated_at']}")

    failed_counts = gate_summary.get("failed_rule_counts") or {}
    if failed_counts:
        st.caption("Failed rule counts: " + " · ".join(f"{html.escape(str(key))}: {html.escape(str(value))}" for key, value in failed_counts.items()))

    gate_topics = [topic for topic in gate_report.get("topics", []) if isinstance(topic, dict)]
    if gate_topics:
        for topic in gate_topics[:36]:
            status = str(topic.get("status") or "FAIL")
            failed_rules = ", ".join(str(rule) for rule in topic.get("failed_rules", []) or []) or "none"
            st.markdown(
                f"""
<div class="health-row health-row-{html.escape(status.casefold())}">
    <div class="link-label">{render_status_chip(status)} {html.escape(str(topic.get("id") or ""))} — {html.escape(str(topic.get("title") or ""))}</div>
    <div class="link-path">failed rules: {html.escape(failed_rules)}</div>
</div>
                """,
                unsafe_allow_html=True,
            )


def render_datasets_tab(
    datasets: list[dict[str, Any]],
    practice_cards: list[dict[str, Any]],
) -> None:
    st.markdown(
        render_card(
            "📊 Datasets",
            "CSV-файлы из папки datasets/ рядом с приложением. Предпросмотр читает только первые строки.",
            eyebrow="Build cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

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
        st.markdown(
            render_card(
                "Папка datasets/ не найдена",
                "Создай datasets/ рядом с приложением и положи туда CSV-файлы.",
                eyebrow="Empty state",
                status="BLOCKED",
            ),
            unsafe_allow_html=True,
        )
        return

    if not datasets:
        st.markdown(
            render_card(
                "CSV-файлы не найдены",
                "Добавь df_events.csv, df_matching.csv или df_orders.csv в datasets/.",
                eyebrow="Empty state",
                status="NEEDS REVIEW",
            ),
            unsafe_allow_html=True,
        )
        return

    render_section_eyebrow_block("Registry")
    dataset_cards = []
    for dataset in datasets:
        has_error = bool(dataset.get("error"))
        rows_value = dataset["rows"] if dataset["rows"] is not None else "—"
        columns_value = dataset["columns"] if dataset["columns"] is not None else "—"
        card_body = "".join(
            [
                render_metric_tile("rows", rows_value, status="ERROR" if has_error else "READY"),
                render_metric_tile("cols", columns_value, status="ERROR" if has_error else "READY"),
                render_metric_tile("size", dataset["size"], status="INFO"),
            ]
        )
        dataset_cards.append(
            render_card(
                dataset["name"],
                str(dataset.get("error") or dataset["path"]),
                eyebrow="CSV",
                status="ERROR" if has_error else "READY",
                content_html=f'<div class="home-metric-grid">{card_body}</div>',
            )
        )
    st.markdown(f'<div class="home-card-grid">{"".join(dataset_cards)}</div>', unsafe_allow_html=True)

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
        st.markdown(
            render_card(
                "Датасет не выбран",
                "Выбери CSV в списке выше, чтобы открыть предпросмотр.",
                eyebrow="Dataset preview",
                status="READY",
            ),
            unsafe_allow_html=True,
        )
        return

    if selected.get("error"):
        st.markdown(
            render_card(
                "Не удалось прочитать CSV",
                str(selected["error"]),
                eyebrow=selected["name"],
                status="ERROR",
            ),
            unsafe_allow_html=True,
        )
        return

    preview_data = read_dataset_preview(selected["path"], nrows=50)
    if preview_data["error"]:
        st.markdown(
            render_card(
                "Не удалось открыть предпросмотр",
                str(preview_data["error"]),
                eyebrow=selected["name"],
                status="ERROR",
            ),
            unsafe_allow_html=True,
        )
        return

    render_section_eyebrow_block("Preview")
    selected_tiles = [
        render_metric_tile("Размер", selected["size"], status="INFO"),
        render_metric_tile("Строк", selected["rows"] if selected["rows"] is not None else "—", status="READY"),
        render_metric_tile("Колонок", selected["columns"] if selected["columns"] is not None else "—", status="READY"),
    ]
    st.markdown(
        render_card(
            selected["name"],
            "Метаданные выбранного CSV.",
            eyebrow="Selected dataset",
            status="READY",
            content_html=f'<div class="home-metric-grid">{"".join(selected_tiles)}</div>',
        ),
        unsafe_allow_html=True,
    )

    render_section_eyebrow_block("Первые 50 строк")
    st.dataframe(preview_data["preview"], use_container_width=True)

    render_section_eyebrow_block("Колонки и типы")
    st.dataframe(preview_data["dtypes"], use_container_width=True, hide_index=True)

    render_section_eyebrow_block("Describe: числовые колонки")
    if preview_data["describe"] is None:
        st.markdown(
            render_card(
                "Числовых колонок не найдено",
                "В первых строках нет numeric-полей для describe().",
                eyebrow="Dataset profile",
                status="NEEDS REVIEW",
            ),
            unsafe_allow_html=True,
        )
    else:
        st.dataframe(preview_data["describe"], use_container_width=True)


def render_scratch_tab(datasets: list[dict[str, Any]]) -> None:
    st.markdown(
        render_card(
            "⚡ Scratch",
            "Лёгкий текстовый раннер: код выполняется отдельным Python-процессом, без живого состояния и без рендера графиков.",
            eyebrow="Build cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    if "scratch_code" not in st.session_state:
        st.session_state["scratch_code"] = default_scratch_code(datasets)

    render_section_eyebrow_block("Runner")
    st.markdown(
        """
<div class="console-panel">
    <div class="phead"><span class="dot3"><i></i><i></i><i></i></span><span>python · scratch process</span></div>
    <div class="editor">Код запускается изолированно: без состояния Notebook и без rich output.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

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
        st.markdown(
            render_card(
                "Простой редактор",
                "streamlit-ace не установлен, поэтому открыт стандартный text_area.",
                eyebrow="Editor fallback",
                status="READY",
            ),
            unsafe_allow_html=True,
        )
        st.text_area("Python code", height=360, key="scratch_code")

    if st.button("▶ Запустить", key="run_scratch", use_container_width=True):
        result = run_scratch_code(st.session_state["scratch_code"], int(timeout_seconds))
        chip = "ERROR" if result["timed_out"] else ("PASS" if result["exit_code"] == 0 else "FAIL")
        st.markdown(
            render_card(
                "Scratch result",
                f"exit code: {result['exit_code']} · time: {result['elapsed']:.2f}s",
                eyebrow="Run result",
                status=chip,
                extra_class="run-result",
            ),
            unsafe_allow_html=True,
        )
        if result["timed_out"]:
            st.warning(f"⏱ таймаут после {timeout_seconds} сек")

        render_section_eyebrow_block("stdout")
        st.code(result["stdout"] or "", language="text")
        render_section_eyebrow_block("stderr")
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
<div class="console-panel">
    <div class="phead"><span class="dot3"><i></i><i></i><i></i></span><span>python · cell {index}</span></div>
    <div class="editor">Код выполняется в живом Python-ядре, состояние сохраняется между ячейками.</div>
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
        loading_slot = st.empty()
        with st.spinner("Ячейка выполняется в Python-ядре..."):
            render_kernel_loading_skeleton(loading_slot)
            st.caption("UI живой: можно прервать ядро сверху или нажать «Обновить вывод».")
        loading_slot.empty()

    render_section_eyebrow_block("Output")
    if outputs:
        st.markdown('<div class="run-result">', unsafe_allow_html=True)
        for output in outputs:
            render_notebook_output(output)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            render_card(
                "Вывода пока нет",
                "Запусти ячейку, чтобы увидеть stdout, rich output или traceback.",
                eyebrow="Notebook output",
                status="READY",
            ),
            unsafe_allow_html=True,
        )


def render_notebook_tab() -> None:
    st.markdown(
        render_card(
            "📓 Notebook",
            "Живое Python-ядро для экспериментов: переменные, импорты, датафреймы и модели сохраняются между ячейками.",
            eyebrow="Build cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
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

    kernel_chip = {
        "idle": "READY",
        "busy": "IN PROGRESS",
        "dead": "ERROR",
    }.get(status_label, "NEEDS REVIEW")
    st.markdown(
        render_card(
            "Kernel state",
            f"cwd: {PROJECT_ROOT}",
            eyebrow="Notebook runtime",
            status=kernel_chip,
            content_html=f'<div class="muted-small mono">kernel: {html.escape(status_label)}</div>',
        ),
        unsafe_allow_html=True,
    )

    if kernel_state.get("last_error"):
        st.warning(kernel_state["last_error"])

    if KernelManager is None:
        st.markdown(
            render_card(
                "Notebook runtime недоступен",
                "Notebook требует jupyter_client и ipykernel. Установи зависимости из requirements.txt.",
                eyebrow="Missing dependency",
                status="ERROR",
            ),
            unsafe_allow_html=True,
        )
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
        st.markdown(
            render_card(
                "Ядро остановлено",
                "Нажми «Перезапустить ядро», чтобы продолжить работу.",
                eyebrow="Notebook runtime",
                status="ERROR",
            ),
            unsafe_allow_html=True,
        )
        return

    render_section_eyebrow_block("Cells")
    for index, cell in enumerate(st.session_state["notebook_cells"], start=1):
        render_notebook_cell(cell, index, kernel_state)


def render_progress(
    sections: dict[str, list[dict[str, str]]],
    practice_cards: list[dict[str, Any]],
    algorithm_lessons: list[dict[str, Any]],
    mentor_tasks: list[dict[str, Any]],
    data_lab_projects: list[dict[str, Any]],
) -> None:
    notes = all_notes(sections)
    total = len(notes)
    done = sum(1 for note in notes if get_note_status(note) == STATUS_DONE)
    reading = sum(1 for note in notes if get_note_status(note) == STATUS_READING)
    repeat = sum(1 for note in notes if get_note_status(note) == STATUS_REPEAT)
    not_started = total - done - reading - repeat
    ratio = completion_ratio(notes)

    st.markdown(
        render_card(
            "Progress",
            "Здесь видно, превращается ли база в реальный учебный путь.",
            eyebrow="Learn cluster",
            status="IN PROGRESS" if ratio < 1 else "PASS",
        ),
        unsafe_allow_html=True,
    )
    note_tiles = [
        render_metric_tile("Готово", done, total=total, progress=ratio, status="PASS" if ratio == 1 and total else "IN PROGRESS"),
        render_metric_tile("Читаю", reading, status="IN PROGRESS"),
        render_metric_tile("Повторить", repeat, status="WEAK" if repeat else "READY"),
        render_metric_tile("Не начато", not_started, status="TODO" if not_started else "READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(note_tiles)}</div>', unsafe_allow_html=True)

    practice_stats = practice_progress(practice_cards)
    render_section_eyebrow_block("Практика")
    practice_total = practice_stats["total"]
    practice_done = practice_stats[PRACTICE_DONE]
    practice_ratio = practice_done / practice_total if practice_total else 0.0
    st.markdown(
        f'<div class="home-metric-grid">{"".join([render_metric_tile("Карточек", practice_total, status="INFO"), render_metric_tile("В работе", practice_stats[PRACTICE_DOING], status="IN PROGRESS"), render_metric_tile("Сделано", practice_done, total=practice_total, progress=practice_ratio, status="PASS" if practice_ratio == 1 and practice_total else "IN PROGRESS")])}</div>',
        unsafe_allow_html=True,
    )

    mentor_stats = mentor_tasks_progress(mentor_tasks)
    mentor_total = mentor_stats["total"]
    mentor_done = mentor_stats["done"]
    mentor_ratio = mentor_done / mentor_total if mentor_total else 0.0
    render_section_eyebrow_block("Mentor tasks")
    st.markdown(
        f'<div class="home-metric-grid">{"".join([render_metric_tile("Автозадач", mentor_total, status="INFO"), render_metric_tile("Решено", mentor_done, total=mentor_total, progress=mentor_ratio, status="PASS" if mentor_ratio == 1 and mentor_total else "IN PROGRESS")])}</div>',
        unsafe_allow_html=True,
    )

    data_lab_stats = data_lab_projects_progress(data_lab_projects)
    data_lab_total = data_lab_stats["projects_total"]
    data_lab_done = data_lab_stats["projects_done"]
    data_lab_ratio = data_lab_done / data_lab_total if data_lab_total else 0.0
    render_section_eyebrow_block("Data Lab Projects")
    data_lab_milestone_meta = f"milestones: {data_lab_stats['milestones_done']}/{data_lab_stats['milestones_total']}"
    data_lab_tiles = [
        render_metric_tile("Проектов", data_lab_total, status="INFO"),
        render_metric_tile(
            "Complete",
            data_lab_done,
            total=data_lab_total,
            progress=data_lab_ratio,
            meta=data_lab_milestone_meta,
            status="PASS" if data_lab_ratio == 1 and data_lab_total else "IN PROGRESS",
        ),
    ]
    st.markdown(
        f'<div class="home-metric-grid">{"".join(data_lab_tiles)}</div>',
        unsafe_allow_html=True,
    )

    algorithm_stats = algorithm_progress(algorithm_lessons)
    algorithm_total = algorithm_stats["total"]
    algorithm_done = algorithm_stats["done"]
    algorithm_ratio = algorithm_done / algorithm_total if algorithm_total else 0.0
    render_section_eyebrow_block("Algorithms Lab")
    st.markdown(
        f'<div class="home-metric-grid">{"".join([render_metric_tile("Уроков", algorithm_total, status="INFO"), render_metric_tile("Пройдено", algorithm_done, total=algorithm_total, progress=algorithm_ratio, status="PASS" if algorithm_ratio == 1 and algorithm_total else "IN PROGRESS")])}</div>',
        unsafe_allow_html=True,
    )

    arena_stats = interview_arena_progress_summary()
    render_section_eyebrow_block("Interview Arena")
    st.markdown(
        f'<div class="home-metric-grid">{"".join([render_metric_tile("Algorithm attempts", arena_stats["algorithm_attempts"], status="INFO"), render_metric_tile("Mock sessions", arena_stats["mock_sessions_completed"], status="READY"), render_metric_tile("Interview answers", arena_stats["interview_answers"], status="INFO"), render_metric_tile("Repeat later", arena_stats["questions_repeat_later"], status="WEAK" if arena_stats["questions_repeat_later"] else "READY")])}</div>',
        unsafe_allow_html=True,
    )

    output_stats = portfolio_progress(practice_cards)
    output_total = output_stats["total"]
    output_done = output_stats["with_outputs"]
    output_ratio = output_done / output_total if output_total else 0.0
    render_section_eyebrow_block("Portfolio outputs")
    st.markdown(
        f'<div class="home-metric-grid">{"".join([render_metric_tile("Output записан", output_done, total=output_total, progress=output_ratio, status="PASS" if output_ratio == 1 and output_total else "IN PROGRESS"), render_metric_tile("Без output", output_stats["missing"], status="TODO" if output_stats["missing"] else "READY")])}</div>',
        unsafe_allow_html=True,
    )

    next_note = find_next_note(sections)
    if next_note:
        section_label = humanize_section_name(next_note["section_key"])
        st.markdown(
            render_card(
                "Что открыть дальше",
                f"{section_label} / {next_note['display_name']}",
                eyebrow="Next note",
                status=note_status_to_chip(get_note_status(next_note)),
            ),
            unsafe_allow_html=True,
        )
        st.button(
            "Перейти к следующей заметке",
            key="progress_open_next",
            on_click=open_note_from_roadmap,
            args=(next_note,),
            use_container_width=True,
        )

    render_section_eyebrow_block("По разделам")
    for section_key, section_notes in sections.items():
        stats = section_progress(section_notes)
        total_section = stats["total"]
        ratio_section = stats[STATUS_DONE] / total_section if total_section else 0.0
        st.markdown(
            render_card(
                humanize_section_name(section_key),
                f"{stats[STATUS_DONE]}/{total_section} готово · {stats[STATUS_READING]} читаю · {stats[STATUS_REPEAT]} повторить",
                eyebrow="Vault section",
                status="PASS" if ratio_section == 1 and total_section else "IN PROGRESS",
                content_html=render_metric_tile("Progress", stats[STATUS_DONE], total=total_section, progress=ratio_section, status="PASS" if ratio_section == 1 and total_section else "IN PROGRESS"),
            ),
            unsafe_allow_html=True,
        )


def open_source_note(note: dict[str, str]) -> None:
    set_active_note(note, push_history=False)
    st.session_state["active_tab"] = "Theory"


def render_problem_link(record: dict[str, Any], index: int, prefix: str) -> None:
    source_note = record["source_note"]
    target = str(record.get("target") or "")
    reason = str(record.get("reason") or "")
    label = str(record.get("label") or target)
    row_class = "health-row-error" if prefix == "broken" else "health-row-fail"
    st.markdown(
        f"""
<div class="health-row {row_class}">
    <div class="link-label">{render_status_chip('ERROR' if prefix == 'broken' else 'NEEDS REVIEW')} {html.escape(label)}</div>
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
    )


def render_links_health(graph: dict[str, Any]) -> None:
    st.markdown(
        render_card(
            "🔗 Links Health",
            "Аудит всех Obsidian-ссылок в vault. Это карта надежности твоей базы.",
            eyebrow="Output cluster",
            status="READY",
        ),
        unsafe_allow_html=True,
    )

    if st.button("Пересканировать ссылки", key="rescan_links"):
        scan_link_graph.clear()
        st.rerun()

    summary = graph["summary"]
    total_links = summary["total"] or 0
    resolved_ratio = summary["resolved"] / total_links if total_links else 0.0
    metric_tiles = [
        render_metric_tile("Всего ссылок", summary["total"], status="INFO"),
        render_metric_tile("Резолвится", summary["resolved"], total=summary["total"], progress=resolved_ratio, status="PASS" if resolved_ratio == 1 and total_links else "IN PROGRESS"),
        render_metric_tile("Битые", summary["broken"], status="ERROR" if summary["broken"] else "READY"),
        render_metric_tile("Неоднозначные", summary["ambiguous"], status="NEEDS REVIEW" if summary["ambiguous"] else "READY"),
    ]
    st.markdown(f'<div class="home-metric-grid">{"".join(metric_tiles)}</div>', unsafe_allow_html=True)

    if summary["broken"] == 0 and summary["ambiguous"] == 0:
        st.markdown(
            render_card(
                "Все ссылки на месте",
                "Битых и неоднозначных Obsidian-ссылок не найдено.",
                eyebrow="Links Health",
                status="PASS",
            ),
            unsafe_allow_html=True,
        )
        return

    broken = graph["broken"]
    ambiguous = graph["ambiguous"]

    if broken:
        render_section_eyebrow_block("Битые ссылки")
        for index, record in enumerate(broken):
            render_problem_link(record, index, "broken")
    else:
        st.markdown(render_card("Битых ссылок нет", "Все targets резолвятся по текущему индексу vault.", eyebrow="Links Health", status="PASS"), unsafe_allow_html=True)

    if ambiguous:
        render_section_eyebrow_block("Неоднозначные ссылки")
        st.caption("Приложение выбирает ближайшую заметку по дереву, но лучше уточнить путь в Obsidian-ссылке.")
        for index, record in enumerate(ambiguous):
            render_problem_link(record, index, "ambiguous")
    else:
        st.markdown(render_card("Неоднозначных ссылок нет", "Каждая ссылка указывает на один понятный target.", eyebrow="Links Health", status="PASS"), unsafe_allow_html=True)


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

    env_vault_path = os.environ.get("VAULT_PATH", "").strip()
    if "vault_path" not in st.session_state:
        st.session_state["vault_path"] = env_vault_path
    st.session_state.setdefault("note_history", [])

    vault_path = st.session_state.get("vault_path", "").strip()
    if not vault_path:
        st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
        st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
        render_breadcrumb("Theory")
        render_vault_setup_card(
            "Vault не подключён",
            "Укажи путь к Obsidian vault в сайдбаре или через VAULT_PATH, чтобы открыть Theory и Theory Quality.",
        )
        render_help()
        render_status_bar()
        return

    vault = Path(vault_path).expanduser()
    if not vault.exists() or not vault.is_dir():
        st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
        st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
        render_breadcrumb("Theory")
        render_vault_setup_card(
            "Vault не найден",
            f"Проверь путь в сайдбаре или VAULT_PATH: {vault_path}",
            status="ERROR",
        )
        render_help()
        render_status_bar()
        return

    resolved_vault = vault.resolve()
    sections = scan_vault(str(resolved_vault))
    if not sections:
        st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
        st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
        render_breadcrumb("Theory")
        render_vault_setup_card(
            "Markdown-файлы не найдены",
            "Добавь .md заметки в vault или укажи другую папку в сайдбаре.",
        )
        render_help()
        render_status_bar()
        return

    note_index = build_note_index(sections)
    graph = scan_link_graph(str(resolved_vault))
    practice_cards, practice_warnings = scan_practice_cards()
    datasets = scan_datasets(DATASETS_DIR)
    algorithm_lessons = scan_algorithm_lessons()
    interview_data = load_interview_questions()
    architecture_data = load_architecture_guidelines()
    mentor_data = load_mentor_tasks(MENTOR_TASKS_PATH)
    project_recipes = scan_data_lab_projects()
    data_lab_projects = [
        project for project in project_recipes if str(project.get("track") or "").casefold() == "data lab"
    ]
    ml_lab_projects = [
        project for project in project_recipes if str(project.get("track") or "").casefold() == "classic ml"
    ]
    if st.session_state.get("active_tab") not in TAB_OPTIONS:
        st.session_state["active_tab"] = "Home"
    st.sidebar.markdown('<div class="sidebar-logo">📚 Learning Sandbox</div>', unsafe_allow_html=True)
    st.sidebar.text_input("Путь к Obsidian vault", key="vault_path")
    st.sidebar.divider()
    active_tab = render_grouped_navigation()
    selected_section, selected_note = render_sidebar(sections)
    render_breadcrumb(active_tab)

    if active_tab == "Home":
        render_dashboard(
            sections,
            practice_cards,
            datasets,
            graph,
            mentor_data,
            project_recipes,
            algorithm_lessons,
            interview_data,
            load_json_report(THEORY_AUDIT_REPORT_PATH),
            load_json_report(COVERAGE_REPORT_PATH),
        )
    elif active_tab == "Theory":
        if selected_note is None:
            st.markdown(
                render_card(
                    "Заметка не выбрана",
                    "Выбери заметку в сайдбаре или очисти поиск, если список пуст.",
                    eyebrow="Theory",
                    status="TODO",
                ),
                unsafe_allow_html=True,
            )
            render_status_bar()
            return
        render_theory_search_box(sections, practice_cards, mentor_data.get("tasks", []))
        render_note(
            selected_section,
            selected_note,
            resolved_vault,
            note_index,
            graph,
            sections,
            practice_cards,
            mentor_data.get("tasks", []),
        )
    elif active_tab == "🎯 Practice":
        render_practice_tab(practice_cards, practice_warnings, note_index, datasets)
    elif active_tab == "🎯 Tasks":
        render_tasks_tab(mentor_data)
    elif active_tab == "🧪 Data Lab Projects":
        render_data_lab_projects_tab(data_lab_projects, datasets, practice_cards, mentor_data.get("tasks", []), note_index)
    elif active_tab == "🤖 ML Lab":
        render_data_lab_projects_tab(
            ml_lab_projects,
            datasets,
            practice_cards,
            mentor_data.get("tasks", []),
            note_index,
            title="🤖 ML Lab",
            description="Classic ML projects: baseline modeling, leakage checks, metrics, model cards, and experiment logs.",
        )
    elif active_tab == "🧪 Experiments":
        render_experiments_tab(project_recipes)
    elif active_tab == "📁 Portfolio":
        render_portfolio_tab(practice_cards, project_recipes)
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
        render_progress(sections, practice_cards, algorithm_lessons, mentor_data.get("tasks", []), project_recipes)
    else:
        render_links_health(graph)
    render_status_bar()


if __name__ == "__main__":
    main()
