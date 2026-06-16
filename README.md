# Hub_ML

Local Streamlit learning sandbox for ML, NLP, data analysis, interview prep, algorithms, and notebook-style experimentation.

## Run

```bash
pip install -r requirements.txt
VAULT_PATH="/absolute/path/to/obsidian_vault" streamlit run app.py
```

## Main Modules

- Theory: Obsidian markdown navigator with wiki links and backlinks.
- Practice: markdown task cards from `practice/`.
- Datasets: CSV previews from `datasets/`.
- Scratch: lightweight subprocess Python runner.
- Notebook: live Jupyter kernel with rich output.
- Algorithms: VKAT livecoding lessons from `content/source/vkat/VKAT-main/algos_patterns/`.
- Interviews: ML/DS interview questions grouped by company.
- Architecture: architecture guidelines study material.
- Portfolio: practice outputs and reflections.

## Notes

- No external AI API calls are made by the app.
- `.learning_progress.json` is local user state and is intentionally ignored by git.
- Raw take-home source archives are kept local unless explicitly promoted into the app.
