# Hub_ML

Local Streamlit workstation for ML/NLP learning, data analysis practice, notebook experimentation, algorithms, interview prep, and portfolio artifacts.

Hub_ML is intentionally simple: one Streamlit entrypoint, local files, no external AI API calls, no database, no auth, no Docker, and no web backend.

## Run

```bash
pip install -r requirements.txt
VAULT_PATH="/absolute/path/to/obsidian_vault" streamlit run app.py
```

`VAULT_PATH` points to an Obsidian vault with markdown notes. If it is not set, the app asks for the vault path in the sidebar.

## Current v0.1 Modules

- Theory: Obsidian markdown navigator with sections, frontmatter chips, wiki links, backlinks, and Links Health.
- Practice: guided markdown practice cards from `practice/`.
- Data Visualization: guided visualization cards based on mentor `analysis_4_visualizations` assignments, with rubric/self-review instead of asserts.
- Mentor Tasks: extracted notebook exercises from `content/extracted/mentor_tasks.json`, checked with official asserts.
- Datasets: CSV registry and previews from `datasets/`.
- Scratch: lightweight text-only subprocess runner for quick Python snippets.
- Notebook: live Jupyter kernel with persistent state and rich output for pandas tables and matplotlib images.
- Algorithms: VKAT livecoding lessons from `content/source/vkat/VKAT-main/algos_patterns/`.
- Interviews: ML/DS interview questions grouped by company.
- Architecture: architecture guidelines study material.
- Portfolio: saved practice outputs and reflections.
- Progress: local reading/practice/task/algorithm progress from `.learning_progress.json`.

## Project Structure

```text
app.py                                  # Streamlit entrypoint and page UI
core/
  notebook/                            # Jupyter kernel lifecycle and output rendering
  tasks/                               # Mentor task normalization, loading, checks, result classification
  datasets/                            # CSV discovery and preview helpers
practice/                              # Guided markdown practice cards
datasets/                              # Local CSV files used by practice/tasks/notebook
content/extracted/mentor_tasks.json     # Extracted mentor tasks with assert checks
content/source/vkat/VKAT-main/algos_patterns/
tests/                                 # Minimal pure-function regression tests
```

## Local State

`.learning_progress.json` stores local progress and portfolio notes. It is intentionally ignored by git.

Ignored local/source material includes raw VKAT notebooks, local virtualenvs, Streamlit home data, login HTMLs, test vaults, and raw take-home archives.

## Checks

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile app.py core/notebook/kernel.py core/notebook/output.py core/tasks/models.py core/tasks/loader.py core/tasks/runner.py core/datasets/registry.py tests/test_tasks.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_tasks.py -q -p no:cacheprovider
```

Manual release checklist: [docs/manual_test_checklist.md](docs/manual_test_checklist.md)

Architecture notes: [docs/architecture.md](docs/architecture.md)
