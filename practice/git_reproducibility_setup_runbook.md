---
title: Git Reproducibility Setup Runbook
section: Git and Tools
difficulty: easy
est_time: 35 мин
related_note: 05_IT_Resources/Git/Reproducible_Environment.md
links:
  - https://git-scm.com/book/en/v2
---

# Git Reproducibility Setup Runbook

## Что сделать

Проверь, что маленький локальный ML/DS проект можно воспроизвести по README-командам. Можно использовать Hub_ML как пример, но не меняй код приложения.

Сделай runbook:

1. Какая команда создаёт virtual environment.
2. Какая команда ставит dependencies из `requirements.txt`.
3. Какая команда запускает проверки.
4. Какие dataset paths ожидаются.
5. Какие файлы должны быть в `.gitignore`.
6. Какие experiment notes нужно записать после запуска.

Мини-чек:

```bash
git status
python --version
python -m pip install -r requirements.txt
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
```

Если работаешь внутри Hub_ML, используй `.venv/bin/python` вместо системного Python.

## Как себя проверить

- В runbook есть точные команды, а не "запустить как обычно".
- Dependency source назван явно: `requirements.txt`.
- Dataset paths относительные, например `datasets/df_orders.csv`.
- `.learning_progress.json`, `.venv/`, caches and `user_projects/` не должны попадать в commit.
- Ты можешь объяснить, какой результат проверки считается успешным.
- Для эксперимента записаны seed/split rule или честная пометка, что их нет.

## Что положить в портфолио

Раздел "Reproducibility": setup commands, test command, expected dataset paths, ignored local files, and a short note explaining how another person can reproduce the project locally.
