# Manual Test Checklist

Use this checklist before tagging a local v0.1 release.

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
- Practice opens existing cards from `practice/`.
- Tasks opens mentor tasks from `content/extracted/mentor_tasks.json`.
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

## Algorithms

- Algorithm lessons list from `content/source/vkat/VKAT-main/algos_patterns/`.
- Opening a lesson shows theory/docstring and source code.
- Running tests on `03_hashmap_pattern.py` succeeds.

## Progress And Portfolio

- Progress shows notes, practice, mentor tasks, algorithms, and portfolio counts.
- Portfolio output can be saved for a practice card.
- `.learning_progress.json` is created/updated locally and is not staged by git.

## Release Gate

- `git status` contains only intended files before commit.
- `.learning_progress.json` is ignored.
- Raw VKAT notebooks and local source archives are ignored.
- Compile check passes.
- Pytest passes.
- Streamlit starts and responds over HTTP.
