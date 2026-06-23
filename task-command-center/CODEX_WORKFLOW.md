# Codex Workflow

Ты можешь писать Codex обычным языком, а Codex будет превращать запросы в команды `taskctl.py`.

## Примеры запросов

Запрос:

```text
Создай карточку CRM login в Today, P1, дедлайн 21 июня
```

Команда:

```bash
python taskctl.py new --title "CRM - login" --project CRM --priority P1 --list Today --due "2026-06-21"
```

Запрос:

```text
Создай карточку и поставь рабочий блок завтра с 10:00 до 12:00
```

Команда:

```bash
python taskctl.py new \
  --title "CRM - сделать страницу логина" \
  --project CRM \
  --priority P1 \
  --list Today \
  --due "2026-06-21" \
  --description "Сделать страницу входа по email/password" \
  --calendar-start "tomorrow 10:00" \
  --calendar-end "tomorrow 12:00" \
  --reminder 30
```

Запрос:

```text
Перемести CRM login в In Progress
```

Команда:

```bash
python taskctl.py move --card "CRM - login" --to "In Progress"
```

Запрос:

```text
Покажи все задачи Today
```

Команда:

```bash
python taskctl.py list --list Today
```

Запрос:

```text
Покажи все P1-задачи
```

Команда:

```bash
python taskctl.py list --priority P1
```

Запрос:

```text
Покажи все задачи проекта CRM
```

Команда:

```bash
python taskctl.py list --project CRM
```

Запрос:

```text
Создай рабочий блок завтра с 10:00 до 12:00
```

Команда:

```bash
python taskctl.py calendar \
  --title "Работа над CRM login" \
  --start "tomorrow 10:00" \
  --end "tomorrow 12:00" \
  --reminder 30
```

Запрос:

```text
Проверь подключение Google Calendar
```

Команда:

```bash
python taskctl.py calendar-test
```

Codex должен проверить, что `client_secret.json` лежит в папке проекта, а `token.json` не коммитится. Если OAuth попросит вход, нужно пройти его в браузере.

Запрос:

```text
Закрой задачу CRM login и добавь summary
```

Команда:

```bash
python taskctl.py done \
  --card "CRM - login" \
  --summary "Сделана форма логина, валидация и обработка ошибок"
```

Запрос:

```text
Разбей задачу оплаты на подзадачи
```

Что делает Codex:

1. Формулирует маленькие результаты.
2. Создает отдельные Trello-карточки.
3. Ставит им проекты, приоритеты и списки.
4. По необходимости добавляет рабочие блоки в Google Calendar.

Запрос:

```text
Почисти Inbox и предложи, куда раскидать задачи
```

Что делает Codex:

1. Запускает `python taskctl.py list --list Inbox`.
2. Группирует задачи по проектам и срочности.
3. Предлагает перемещения.
4. После подтверждения двигает карточки командами `move`.

Запрос:

```text
Добавь ссылку на PR в карточку
```

Команда:

```bash
python taskctl.py link \
  --card "CRM - login" \
  --url "https://github.com/username/crm-app/pull/12"
```

Запрос:

```text
Удали тестовую карточку CRM
```

Команда:

```bash
python taskctl.py delete --card "CRM - тестовая карточка" --yes
```

Запрос:

```text
Создай карточку и календарный блок одной командой
```

Команда:

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
