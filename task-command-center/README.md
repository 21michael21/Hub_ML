# Task Command Center

Бесплатная система управления задачами для нескольких проектов:

- Trello - главная доска задач.
- Google Calendar - рабочие блоки и напоминания.
- `taskctl.py` - локальный Python CLI, которым может управлять Codex CLI.
- Без Zapier, Make, Todoist Pro, Notion AI и других платных связок.

## Структура

```text
task-command-center/
  README.md
  TASK_RULES.md
  CODEX_WORKFLOW.md
  SETUP.md
  .gitignore
  .env.example
  config.example.yaml
  requirements.txt
  taskctl.py
  src/
  examples/
```

## Быстрый старт в mock-режиме

```bash
cd task-command-center
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
python taskctl.py new \
  --title "CRM - сделать страницу логина" \
  --project CRM \
  --priority P1 \
  --list Today \
  --due "2026-06-21" \
  --description "Сделать страницу входа по email/password" \
  --calendar-start "2026-06-18 10:00" \
  --calendar-end "2026-06-18 12:00" \
  --reminder 30
python taskctl.py list --list Today
```

Mock-режим включается переменной:

```dotenv
TASKCTL_MOCK=1
```

Он не ходит в Trello и Google Calendar, а пишет данные в `.taskctl_mock/`.

## Trello board

Создай board:

```text
Command Center
```

Создай списки:

- `Inbox`
- `Backlog`
- `Next`
- `Today`
- `In Progress`
- `Waiting`
- `Review`
- `Done`

Создай labels проектов:

- `CRM`
- `Landing`
- `Bot`
- `Database`
- `Docs`
- `Learning`
- `Personal`
- `Finance`

Создай labels приоритетов:

- `P1`
- `P2`
- `P3`

## Trello API key, token и board_id

API key и token:

1. Открой https://trello.com/power-ups/admin
2. Создай Power-Up или выбери существующий.
3. Скопируй API key.
4. На странице API key создай token.
5. Запиши их в `.env`:

```dotenv
TRELLO_API_KEY=...
TRELLO_TOKEN=...
```

Board ID:

1. Открой board `Command Center`.
2. Добавь `.json` в конец URL доски.
3. Найди поле `id`.
4. Запиши:

```dotenv
TRELLO_BOARD_ID=...
```

## Google Calendar API

1. Открой Google Cloud Console: https://console.cloud.google.com/
2. Включи Google Calendar API.
3. Создай OAuth Client ID типа `Desktop app`.
4. Скачай credentials JSON.
5. Переименуй файл в `client_secret.json`.
6. Положи файл в папку проекта:

```text
task-command-center/client_secret.json
```

7. Запиши в `.env`:

```dotenv
GOOGLE_CLIENT_SECRET_FILE=client_secret.json
GOOGLE_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary
```

При первом реальном запуске Calendar-команды откроется OAuth-окно, а затем будет создан `token.json`.

`token.json` не нужно коммитить. Это локальный OAuth token с доступом к твоему Google Calendar; он уже добавлен в `.gitignore`.

Первый тест календаря:

```bash
python taskctl.py calendar-test
```

Команда проверит `client_secret.json`, `GOOGLE_CALENDAR_ID`, timezone, запустит OAuth flow при необходимости, создаст тестовое событие на 15 минут и reminder за 5 минут. Событие не удаляется автоматически.

Если `token.json` был создан со старым readonly scope, удали `token.json` и запусти `calendar-test` снова. Для создания событий нужен scope:

```text
https://www.googleapis.com/auth/calendar
```

## Календарь Task Command Center

Можно использовать `primary`, но лучше создать отдельный календарь:

```text
Task Command Center
```

После создания найди Calendar ID в настройках календаря и запиши его в `.env`:

```dotenv
GOOGLE_CALENDAR_ID=your_calendar_id
```

## iPhone и MacBook

Trello:

- Установи Trello на iPhone и MacBook или используй браузер.
- Войди в один Trello account.
- Закрепи board `Command Center`.

Google Calendar:

- Добавь Google account на iPhone и оба MacBook.
- Включи календарь `Task Command Center`.
- Проверь, что уведомления Google Calendar разрешены на всех устройствах.
- После `python taskctl.py calendar-test` проверь, что тестовое событие появилось на iPhone.
- Убедись, что reminder за 5 минут приходит на iPhone и второй MacBook.

Так события и напоминания, созданные через CLI, будут синхронизироваться на iPhone и MacBook.

## Trello due date vs Google Calendar event

`Trello due date` - дедлайн результата.

`Google Calendar event` - время, когда ты реально работаешь над задачей, или короткое напоминание.

Пример:

- Карточка `CRM - сделать страницу логина` имеет due date `2026-06-21`.
- В календаре есть рабочий блок `2026-06-18 10:00-12:00`.

Дедлайн говорит "когда должно быть готово". Календарь говорит "когда я это делаю".

## Использование через Codex CLI

Пиши Codex обычным языком:

```text
Создай карточку CRM login в Today, P1, дедлайн 21 июня.
```

Codex запускает:

```bash
python taskctl.py new --title "CRM - login" --project CRM --priority P1 --list Today --due "2026-06-21"
```

Больше примеров: [CODEX_WORKFLOW.md](CODEX_WORKFLOW.md) и [examples/commands.md](examples/commands.md).

## Карточка плюс календарь

```bash
python taskctl.py new \
  --title "TASKCTL TEST - Trello plus Calendar" \
  --project Personal \
  --priority P3 \
  --list Today \
  --due "2026-06-21" \
  --description "Проверка создания карточки Trello и события Google Calendar одной командой." \
  --calendar-start "2026-06-18 12:00" \
  --calendar-end "2026-06-18 12:15" \
  --reminder 5
```

Если Google Calendar еще не настроен, команда остановится до создания Trello-карточки.
