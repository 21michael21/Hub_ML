---
title: Git Tools: Commit README Practice
section: Git and Tools
difficulty: easy
est_time: 30 мин
related_note: 05_IT_Resources/Git/Git_CLI_Workflow.md
links:
  - https://git-scm.com/book/en/v2
---

# Git Tools: Commit README Practice

## Что сделать

Сделай безопасную Git-практику в маленькой учебной папке. Не используй destructive commands.

Шаги:

1. Создай отдельную папку `git-practice-demo`.
2. Запусти `git init`.
3. Создай `README.md` с коротким описанием учебного проекта.
4. Выполни `git status` и запиши, что Git показывает.
5. Выполни `git diff` до staging.
6. Сделай `git add README.md`.
7. Снова выполни `git status` и объясни, что изменилось.
8. Сделай commit с понятным сообщением.
9. Выполни `git log --oneline -1`.
10. Добавь вторую строку в README, посмотри `git diff`, но не коммить автоматически.

## Как себя проверить

- Ты не использовал `git reset --hard`, `git clean`, `push --force` или другие destructive commands.
- Ты можешь объяснить разницу между unstaged и staged changes.
- Commit message отвечает на вопрос "что изменилось?".
- Ты прочитал diff до commit.
- В README нет токенов, приватных данных или локальных путей к секретам.
- Ты можешь назвать 3 файла/папки, которые нельзя коммитить в ML/DS проекте.

## Что положить в портфолио

Короткий фрагмент "Git workflow": команда `git log --oneline -1`, commit message, список намеренно некоммитимых файлов и 3 предложения о том, как Git помогает вести ML/DS проект аккуратно.
