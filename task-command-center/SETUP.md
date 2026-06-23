# Setup

## 1. Установка зависимостей

```bash
cd task-command-center
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
```

## 2. Первый локальный тест без API

В `.env` оставь:

```dotenv
TASKCTL_MOCK=1
```

Потом запусти:

```bash
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
```

Проверка:

```bash
python taskctl.py list --list Today
```

Mock-данные появятся в `.taskctl_mock/`.

## 3. Trello

Вручную в Trello:

1. Создай board `Command Center`.
2. Создай списки:
   - `Inbox`
   - `Backlog`
   - `Next`
   - `Today`
   - `In Progress`
   - `Waiting`
   - `Review`
   - `Done`
3. Создай labels проектов:
   - `CRM`
   - `Landing`
   - `Bot`
   - `Database`
   - `Docs`
   - `Learning`
   - `Personal`
   - `Finance`
4. Создай labels приоритетов:
   - `P1`
   - `P2`
   - `P3`

Получение API key и token:

1. Открой https://trello.com/power-ups/admin
2. Создай Power-Up или используй существующий.
3. Скопируй API key.
4. На странице key открой ссылку для token и выдай доступ.
5. Запиши значения в `.env`.

Как узнать `TRELLO_BOARD_ID`:

1. Открой Trello board в браузере.
2. Добавь `.json` в конец URL доски.
3. Найди поле `id`.
4. Запиши его в `.env` как `TRELLO_BOARD_ID`.

## 4. Google Calendar

Вручную в Google Cloud:

1. Открой https://console.cloud.google.com/
2. Создай project или выбери существующий.
3. Включи Google Calendar API.
4. Открой `APIs & Services -> Credentials`.
5. Создай OAuth Client ID типа `Desktop app`.
6. Скачай JSON credentials.
7. Переименуй файл в `client_secret.json`.
8. Положи файл в папку проекта:

```text
task-command-center/client_secret.json
```

9. В `.env` укажи:

```dotenv
GOOGLE_CLIENT_SECRET_FILE=client_secret.json
GOOGLE_TOKEN_FILE=token.json
```

Календарь:

1. Открой Google Calendar.
2. Создай календарь `Task Command Center`.
3. Если хочешь писать в него, а не в основной календарь, найди Calendar ID в настройках календаря.
4. Запиши ID в `.env`:

```dotenv
GOOGLE_CALENDAR_ID=your_calendar_id
```

Для первого реального запуска поставь:

```dotenv
TASKCTL_MOCK=0
```

При первой команде календаря откроется OAuth-окно, после чего появится локальный `token.json`.

`token.json` не нужно коммитить. Это локальный OAuth token с доступом к твоему Google Calendar; он уже добавлен в `.gitignore`.

Первый тест календаря:

```bash
python taskctl.py calendar-test
```

Команда создаст тестовое событие на 15 минут и reminder за 5 минут. Она не удаляет событие автоматически.

Если видишь ошибку про readonly scope, удали `token.json` и запусти `calendar-test` снова. Для создания событий нужен scope:

```text
https://www.googleapis.com/auth/calendar
```

## 5. iPhone и два MacBook

Trello:

- Установи Trello на iPhone и оба MacBook или используй веб-версию.
- Войди в тот же Trello account.
- Открой board `Command Center`.

Google Calendar:

- На iPhone добавь Google account в настройки календаря.
- На обоих MacBook добавь тот же Google account в Calendar или используй Google Calendar в браузере.
- Включи календарь `Task Command Center`.
- Напоминания будут приходить как Google Calendar notifications, если уведомления включены на устройствах.
- После `python taskctl.py calendar-test` открой Google Calendar на iPhone и проверь тестовое событие.
- Дождись reminder за 5 минут или проверь, что уведомления разрешены для Google Calendar.

## 6. Переход с mock на реальные API

1. Заполни `.env`.
2. Поставь `TASKCTL_MOCK=0`.
3. Убедись, что `config.yaml` совпадает с реальными списками и labels в Trello.
4. Запусти:

```bash
python taskctl.py list --list Today
```

Если список читается, Trello подключен. Потом проверь Calendar:

```bash
python taskctl.py calendar-test
```

Проверка карточки и календарного события одной командой:

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
