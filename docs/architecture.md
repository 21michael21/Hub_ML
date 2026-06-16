# Architecture

Hub_ML is a local Streamlit application. It is designed to stay small and file-based.

## Entry Point

`app.py` is the Streamlit entrypoint. It owns page routing, tab UI, sidebar state, progress UI, and feature rendering.

The app intentionally does not use FastAPI, React, a database, Docker, external AI APIs, or authentication.

## Core Modules

### `core/notebook`

Jupyter kernel support lives here.

- `core/notebook/kernel.py`
  - starts and reuses one Jupyter kernel through `jupyter_client`;
  - keeps kernel runtime in Streamlit cache;
  - supports execution, polling, interrupt, restart, and shutdown;
  - is reused by both Notebook and Mentor Tasks.

- `core/notebook/output.py`
  - normalizes kernel messages;
  - renders text output, errors, HTML tables, and PNG images.

### `core/tasks`

Mentor task logic lives here.

- `core/tasks/models.py`
  - normalizes extracted mentor task records;
  - separates user solution starter code from official test code;
  - detects dataset references;
  - infers small setup snippets for dependent pandas tasks.

- `core/tasks/loader.py`
  - loads `content/extracted/mentor_tasks.json`;
  - filters to checkable assert-based tasks;
  - sorts tasks for display.

- `core/tasks/runner.py`
  - builds final task scripts;
  - runs checks through the existing Jupyter kernel path;
  - classifies results as `PASS`, `FAIL`, `ERROR`, `TIMEOUT`, or `KERNEL_BUSY`.

### `core/datasets`

Dataset registry helpers live here.

- `core/datasets/registry.py`
  - scans `datasets/*.csv`;
  - counts rows and columns;
  - reads previews;
  - returns dtypes and numeric summaries.

### `core/projects`

Project-based learning helpers live here.

- `core/projects/models.py`
  - normalizes project recipes and milestones;
  - calculates readiness and completion.

- `core/projects/loader.py`
  - loads project recipes from `content/projects/data_lab/` and `content/projects/ml_lab/`.

- `core/projects/progress.py`
  - stores milestone completion, checklist state, reflection text, and project completion flags through the existing progress file pattern.

- `core/projects/workspace.py`
  - creates ignored local project workspaces under `user_projects/`;
  - writes README, portfolio, notes, milestones, manifest, and artifact folders;
  - refuses to overwrite existing folders unless explicitly requested.

### `core/portfolio`

Portfolio export helpers live here.

- `core/portfolio/exporter.py`
  - builds Markdown templates from completed projects and completed practice cards;
  - avoids inventing results or metrics;
  - writes user-facing output only when the app explicitly asks it to.

### `core/experiments`

Experiment Tracker Lite helpers live here.

- `core/experiments/tracker.py`
  - normalizes local experiment records;
  - saves and loads JSONL records;
  - summarizes and compares runs by user-provided metrics.

### `core/reports`

Read-only report helpers live here.

- `core/reports/theory_quality.py`
  - loads generated theory audit and coverage reports for the app UI.

## Content Sources

### `practice/`

Practice cards are markdown files with YAML frontmatter. Each file is one guided exercise.

Visualization assignments from mentor `analysis_4_visualizations.ipynb` are represented here as guided cards with rubric/self-review, not assert-based Tasks.

### `content/extracted/mentor_tasks.json`

Extracted mentor notebook tasks live here. Only tasks with asserts are used by the Mentor Tasks tab.

### `content/projects/`

Project recipes live here:

- `content/projects/data_lab/`
  - Orders EDA Report;
  - Events Funnel Analysis;
  - Matching Quality Dashboard.

- `content/projects/ml_lab/`
  - Orders Conversion Baseline Classifier.

Recipes are JSON files. They describe goals, datasets, milestones, deliverables,
related theory/practice/tasks, and portfolio prompts.

### `content/reports/`

Generated static reports live here:

- `theory_audit.json` / `theory_audit.md`
- `coverage_report.json` / `coverage_report.md`

### `datasets/`

Local CSV files live here. Current expected files:

- `df_events.csv`
- `df_matching.csv`
- `df_orders.csv`

These files are read by Datasets, Practice, Notebook examples, and Mentor Tasks.

### `content/source/vkat/VKAT-main/algos_patterns/`

Algorithm lessons from mentor material live here. They are loaded by the Algorithms tab.

Raw VKAT notebooks and source data are intentionally ignored by git unless promoted into app content.

## Local Progress

`.learning_progress.json` stores local user state:

- note statuses;
- practice card statuses;
- portfolio outputs;
- algorithm statuses;
- mentor task statuses.
- project milestone statuses;
- project completion flags.

This file is intentionally ignored by git because it is personal local state.

`user_projects/` stores generated project workspaces and is also ignored by git.

## Safety Boundary

Notebook, Scratch, Algorithms, Mentor Tasks, and code project milestones execute local code. Hub_ML is a trusted local workstation, not a secure sandbox for untrusted code.
