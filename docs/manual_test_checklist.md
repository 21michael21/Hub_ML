# Manual Test Checklist

Use this checklist before tagging a local v0.2 release.

## Setup

- Install dependencies:

```bash
pip install -r requirements.txt
```

- Start the app with a real Obsidian vault:

```bash
VAULT_PATH="/absolute/path/to/obsidian_vault" streamlit run app.py
```

## App Navigation

- Home opens without errors.
- Theory opens a markdown note from the vault.
- Theory Quality opens generated audit and coverage summaries.
- Practice opens existing cards from `practice/`.
- Tasks opens mentor tasks from `content/extracted/mentor_tasks.json`.
- Data Lab Projects opens project cards.
- Portfolio opens saved output forms.
- Datasets lists CSV files from `datasets/`.
- Scratch opens and can run a simple print snippet.
- Notebook opens with kernel status visible.
- Algorithms lists VKAT algorithm lessons.
- Interviews lists grouped interview questions.
- Architecture renders the architecture study material.
- Roadmap opens.
- Progress opens.
- Links Health opens and shows link counts.

## Theory

- Frontmatter renders as chips, not raw YAML.
- Wiki links are highlighted in markdown.
- Outgoing links and backlinks render below the note.
- Back navigation works after following a wiki link.

## Practice

- Section filter works.
- `Data Visualization` section appears.
- The 3 visualization cards open:
  - daily order sum line chart;
  - commission histogram;
  - commission by delivery fee boxplot.
- Each visualization card has source, goal, dataset, task, starter code, checklist, self-review, and portfolio suggestion.
- `📊 Открыть датасет` opens `df_orders.csv`.
- `📓 Открыть в Notebook` creates a notebook starter cell when available.
- Practice status changes persist after app refresh.

## Mentor Tasks

- Tasks load from `content/extracted/mentor_tasks.json`.
- Checkable tasks count is 33.
- Low-confidence tasks stay in the review section.
- Smoke task passes:
  - open `🎯 Tasks`;
  - filter to `Pandas`;
  - open `Задание 1: Свойства и статистики`;
  - solve with `pd.read_csv("datasets/df_events.csv")`;
  - verify `rows_count == 378299`;
  - result is `PASS`.

## Datasets

- Expected files appear:
  - `df_events.csv`;
  - `df_matching.csv`;
  - `df_orders.csv`.
- Preview works for each CSV.
- Column types render.
- Numeric describe renders when numeric columns exist.

## Notebook

- Run:

```python
x = 21
```

- Then run:

```python
print(x * 2)
```

- Output is `42`.
- A pandas DataFrame displays as a table.
- A matplotlib plot displays as an image.
- Interrupt works for long-running code.
- Restart clears variables.

## Data Lab And ML Lab Projects

- Data Lab Projects list contains:
  - Orders EDA Report;
  - Events Funnel Analysis;
  - Matching Quality Dashboard.
- Classic ML project appears:
  - Orders Conversion Baseline Classifier.
- Opening a project shows goal, business context, datasets, skills, related theory/practice/tasks, milestones, deliverables, and portfolio prompt.
- Milestone types render without errors:
  - reading;
  - code;
  - visualization;
  - reflection;
  - report;
  - model_card.
- Marking a milestone done updates project progress.
- A project cannot be marked complete unless required milestones are done.
- Dataset buttons open the related dataset when available.
- Related practice/task/theory buttons navigate when available.

## Project Workspace Scaffolder

- In a project detail view, click `Create project workspace`.
- The generated folder appears under `user_projects/`.
- Generated files include:
  - `README.md`;
  - `project.json`;
  - `portfolio.md`;
  - `notes.md`;
  - `milestones.md`;
  - `artifacts/charts/.gitkeep`;
  - `artifacts/tables/.gitkeep`;
  - `src/.gitkeep`.
- Clicking create again does not overwrite the existing folder without explicit confirmation.
- Raw datasets are not copied into the workspace.

## Experiment Tracker Lite

- Open the Classic ML project detail.
- Save a manual experiment record with:
  - model name;
  - dataset names;
  - target column;
  - feature columns;
  - at least one real or manually entered metric;
  - notes.
- The experiment log reloads and shows the saved record.
- The comparison table sorts by the selected metric.
- No raw datasets are written into experiment records.

## Algorithms

- Algorithm lessons list from `content/source/vkat/VKAT-main/algos_patterns/`.
- Opening a lesson shows theory/docstring and source code.
- Running tests on `03_hashmap_pattern.py` succeeds.

## Progress And Portfolio

- Progress shows notes, practice, mentor tasks, algorithms, projects, and portfolio counts.
- Portfolio output can be saved for a practice card.
- Portfolio Export preview can be generated from completed projects and/or completed practice cards.
- Export writes to `portfolio/README.md` or `portfolio/generated_portfolio.md`.
- `.learning_progress.json` is created/updated locally and is not staged by git.

## Release Gate

- `git status` contains only intended files before commit.
- `.learning_progress.json` is ignored.
- `user_projects/` is ignored.
- Raw VKAT notebooks and local source archives are ignored.
- Compile check passes.
- Pytest passes.
- Streamlit starts and responds over HTTP.
