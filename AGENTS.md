# AGENTS.md — Hub_ML

## Stack & boundaries
- Streamlit single-app (`app.py`) + `tools/` + `content/`. Only stdlib + pandas/pytest.
- Do not introduce React/Next/Tauri/FastAPI/MLflow/LangChain/vector DB or any heavy dependency.
- One optional exception is allowed for local search only: `sentence-transformers` may be installed
  from `requirements-embeddings.txt` as an opt-in, local, CPU, free embedding backend. It must never
  be required for tests/runtime, never call an API, and TF-IDF must remain the default fallback.
- Do not add AI APIs and do not implement RAG. External sources are curate + cite: never paste source text, never bulk-generate notes. Auditor flag `likely_ai_dump_or_placeholder = true` is a failure, not a warning.

## Don't break
- Never rename `st.session_state` keys, progress JSON keys, or existing report schemas.
- Do not change `mentor_tasks.json` format or task execution behavior.
- Reuse UI helpers (`render_card` / `render_metric_tile` / `render_status_chip` / `render_section_eyebrow`) and tokens (`--bg` / `--accent` / `--pass` / `--warn` / `--fail` / `--info`).

## Commands (run before "done")
- Tests: `python -m pytest -q`
- Compile: `python -m compileall app.py tools`
- App import: `python -c "import app"`
- Resources: `python tools/validate_resources.py`

## Verification discipline (non-negotiable)
- No vanity checks. Green pytest or "Done" does not prove a checker works.
- Proof = checker `EXIT != 0` on intentionally broken input and `EXIT = 0` on valid input. Show both runs in the report.
- TDD: write the failing test/fixture first, confirm it fails, then implement to green. Do not rewrite tests to fit the result.

## Done means pushed
- A commit is not ready until `git push origin main` succeeds and `git ls-remote origin main` prints the new hash. Paste the hash into the report.

## Change size
- Each commit is a small reviewable stage (< ~500 changed lines). Split bigger work and deliver the smallest complete stage. After the commit, stop and show the diff.

## Out of scope
- `task-command-center/` stays untracked. `.venv` and `user_projects/` stay in `.gitignore`.
