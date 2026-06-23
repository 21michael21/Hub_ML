# Hub_ML quality checks

`tools/run_quality_checks.py` is the local pre-release command for catching runtime,
content, and UI regressions before a manual launch.

## Modes

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/run_quality_checks.py --mode quick
```

Runs:
- compile `app.py core tools tests`
- `pytest` excluding browser E2E
- app import
- resource registry validation

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/run_quality_checks.py --mode ui
```

Runs `quick`, then:
- Streamlit AppTest smoke tests
- raw HTML AppTest sweep
- Playwright E2E when Chromium is installed

Playwright is optional in `ui` mode. To make missing browsers fail the run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/run_quality_checks.py --mode ui --strict-e2e
```

Install browser test dependencies with:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pip install -r requirements-dev.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m playwright install chromium
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/run_quality_checks.py --mode content
```

Runs `quick`, then:
- content gate with `--reaudit`
- internal UI links
- Russian content language audit
- required topic source readiness when the checker exists

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/run_quality_checks.py --mode full
```

Runs `quick`, `ui`, `content`, plus:
- dataset registry smoke for `df_events.csv`, `df_matching.csv`, `df_orders.csv`
- mentor task loading smoke
- optional `df_events` task runner smoke placeholder

The task runner smoke does not execute the live Jupyter kernel because this command must not
mutate user progress or hide task execution side effects.

## Dry run

Print the selected checks without running them:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/run_quality_checks.py --mode full --dry-run
```

## Release habit

Use `quick` while editing, `ui` before visual/manual app testing, `content` after changing
notes/practice/resources, and `full` before release tags.
