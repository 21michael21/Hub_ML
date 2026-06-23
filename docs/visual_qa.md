# Visual QA Screenshots

Hub_ML has a manual screenshot workflow for visual checkpoints. It is meant for human review, not pixel-perfect assertions.

## Install Browser Runtime

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pip install -r requirements-dev.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m playwright install chromium
```

## Capture Screenshots

Default capture uses the committed sample vault and writes ignored local artifacts:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/capture_screenshots.py
```

Default output:

```text
tests/e2e/artifacts/screenshots/
```

Targets:

- `home-cockpit.png`
- `tasks-result.png`
- `projects-detail.png`
- `notebook-output.png`
- `portfolio-export.png`
- `interview-arena.png`
- `theory-quality.png`

Dry run without launching Streamlit or Playwright:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/capture_screenshots.py --dry-run
```

To review a real private vault locally:

```bash
VAULT_PATH="/absolute/path/to/obsidian_vault" \
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/capture_screenshots.py
```

## Manual Inspection Checklist

- No visible `Traceback`, `TypeError`, `KeyError`, raw `<div`, `</div>`, or `class=`.
- Sidebar navigation is reachable and active state is clear.
- Cards have consistent border, hover, spacing, and typography.
- Buttons are aligned with the content container and do not stretch unless they are grouped controls.
- Status chips use the same visual language across pages.
- Empty states explain what is missing and what to do next.
- Notebook/task/project result panels show loading/output states without layout jumps.
- Reduced motion users are protected by `prefers-reduced-motion`.
- Mobile-width captures do not create obvious horizontal overflow.

## Privacy Rules

- Do not commit screenshots containing private vault text, private datasets, raw user outputs, tokens, emails, or personal notes.
- The default artifact directory is ignored by git.
- Curated docs screenshots are optional. Copy only safe screenshots manually into `docs/screenshots/` when preparing a public visual checkpoint.
- Prefer the sample vault for repeatable screenshots in issues, PRs, and design reviews.

## Curated Docs Screenshots

README lists optional curated destinations such as:

```text
docs/screenshots/home-cockpit.png
docs/screenshots/tasks-result.png
docs/screenshots/projects-detail.png
docs/screenshots/notebook-output.png
docs/screenshots/portfolio-export.png
```

Those files should be copied manually from `tests/e2e/artifacts/screenshots/` only after checking that they contain no private content.
