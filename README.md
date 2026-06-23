# Hub_ML

[![CI](https://github.com/21michael21/Hub_ML/actions/workflows/ci.yml/badge.svg)](https://github.com/21michael21/Hub_ML/actions/workflows/ci.yml)

Local Streamlit workstation for ML/NLP learning, data analysis practice, notebook experimentation, algorithms, interview prep, and portfolio artifacts.

Hub_ML is intentionally simple: one Streamlit entrypoint, local files, no external AI API calls, no database, no auth, no Docker, and no web backend.

## Run

```bash
pip install -r requirements.txt
VAULT_PATH="/absolute/path/to/obsidian_vault" streamlit run app.py
```

`VAULT_PATH` points to an Obsidian vault with markdown notes. If it is not set, the app asks for the vault path in the sidebar.

## Current v0.2 Modules

- Theory: Obsidian markdown navigator with sections, frontmatter chips, wiki links, backlinks, and Links Health.
- Theory Quality: read-only quality and coverage summaries from generated audit reports.
- Practice: guided markdown practice cards from `practice/`.
- Data Visualization: guided visualization cards based on mentor `analysis_4_visualizations` assignments, with rubric/self-review instead of asserts.
- Mentor Tasks: extracted notebook exercises from `content/extracted/mentor_tasks.json`, checked with official asserts.
- Datasets: CSV registry and previews from `datasets/`.
- Scratch: lightweight text-only subprocess runner for quick Python snippets.
- Notebook: live Jupyter kernel with persistent state and rich output for pandas tables and matplotlib images.
- Data Lab Projects: end-to-end guided projects with milestones, datasets, theory/practice/task connections, and progress.
- Classic ML Baseline Project: conversion baseline classifier project with scikit-learn milestones and model-card output.
- Project Workspace Scaffolder: local ignored `user_projects/` workspace templates for project artifacts.
- Experiment Tracker Lite: local JSONL experiment logs for ML project runs.
- Algorithms: VKAT livecoding lessons from `content/source/vkat/VKAT-main/algos_patterns/`.
- Interviews: ML/DS interview questions grouped by company.
- Architecture: architecture guidelines study material.
- Portfolio: saved practice outputs, reflections, and markdown portfolio export templates.
- Progress: local reading/practice/task/algorithm/project progress from `.learning_progress.json`.

## Project Structure

```text
app.py                                  # Streamlit entrypoint and page UI
core/
  notebook/                            # Jupyter kernel lifecycle and output rendering
  tasks/                               # Mentor task normalization, loading, checks, result classification
  datasets/                            # CSV discovery and preview helpers
  projects/                            # Project recipes, milestone progress, and workspace scaffolding
  portfolio/                           # Portfolio markdown export helpers
  experiments/                         # Local experiment record helpers
  reports/                             # Theory quality report loading
practice/                              # Guided markdown practice cards
datasets/                              # Local CSV files used by practice/tasks/notebook
content/projects/                      # Data Lab and ML Lab project recipes
content/reports/                       # Theory audit and coverage reports
content/extracted/mentor_tasks.json     # Extracted mentor tasks with assert checks
content/source/vkat/VKAT-main/algos_patterns/
tests/                                 # Minimal pure-function regression tests
```

## Local State

`.learning_progress.json` stores local progress and portfolio notes. It is intentionally ignored by git.

Generated project workspaces live under `user_projects/` and are ignored by git.

Ignored local/source material includes raw VKAT notebooks, local virtualenvs, Streamlit home data, login HTMLs, test vaults, and raw take-home archives.

## Checks

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m compileall -q app.py core tools tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
```

## Running Checks

The full private-vault content gate requires your real Obsidian vault:

```bash
VAULT_PATH="/absolute/path/to/obsidian_vault" PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/check_content_gate.py --reaudit
```

CI uses the committed sample vault to prove the tooling runs without private files. It does not assert `36/36` coverage:

```bash
VAULT_PATH=tests/fixtures/sample_vault PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/check_internal_links.py
VAULT_PATH=tests/fixtures/sample_vault PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/check_content_gate.py --reaudit
```

Optional local pre-commit setup:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pip install -r requirements-dev.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pre-commit install
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pre-commit run --all-files
```

Manual release checklist: [docs/manual_test_checklist.md](docs/manual_test_checklist.md)

Architecture notes: [docs/architecture.md](docs/architecture.md)

## Screenshot Checklist

Before a visual checkpoint, capture screenshots for:

- `docs/screenshots/home-cockpit.png` — Home cockpit with top bar, status tiles, and bottom status bar.
- `docs/screenshots/tasks-result.png` — Mentor Tasks result panel with PASS/FAIL/ERROR chip.
- `docs/screenshots/projects-detail.png` — Data Lab or ML Lab project detail with milestone cards.
- `docs/screenshots/notebook-output.png` — Notebook cell output after running `print(42)`.
- `docs/screenshots/portfolio-export.png` — Portfolio exporter preview.

Screenshots are optional local artifacts; do not commit private data or raw user outputs.
