# Example Commands

## Create a card

```bash
python taskctl.py new \
  --title "CRM - сделать страницу логина" \
  --project CRM \
  --priority P1 \
  --list Today \
  --due "2026-06-21" \
  --description "Сделать страницу входа по email/password" \
  --criteria "Есть форма email/password" \
  --criteria "Есть валидация" \
  --criteria "Ошибки показаны пользователю"
```

## Create a card and calendar block

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

## List cards from Today

```bash
python taskctl.py list --list Today
```

## List P1 cards

```bash
python taskctl.py list --priority P1
```

## List CRM cards

```bash
python taskctl.py list --project CRM
```

## Move a card

```bash
python taskctl.py move \
  --card "CRM - сделать страницу логина" \
  --to "In Progress"
```

## Close a card

```bash
python taskctl.py done \
  --card "CRM - сделать страницу логина" \
  --summary "Сделана форма логина, валидация и обработка ошибок"
```

## Create only a calendar block

```bash
python taskctl.py calendar \
  --title "Работа над CRM login" \
  --start "2026-06-18 10:00" \
  --end "2026-06-18 12:00" \
  --reminder 30
```

## Run Google Calendar OAuth smoke test

```bash
python taskctl.py calendar-test
```

This checks `client_secret.json`, creates `token.json` after OAuth if needed, creates a 15-minute test event, and adds a 5-minute reminder.

## Create a reminder event

```bash
python taskctl.py remind \
  --title "CRM - сделать страницу логина" \
  --at "2026-06-18 10:00" \
  --duration 15 \
  --reminder 30
```

## Create a card and calendar event together

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

## Add a comment

```bash
python taskctl.py comment \
  --card "CRM - сделать страницу логина" \
  --text "Начал работу, проверяю layout"
```

## Add a GitHub link

```bash
python taskctl.py link \
  --card "CRM - сделать страницу логина" \
  --url "https://github.com/username/crm-app/pull/12"
```

## Permanently delete a card

```bash
python taskctl.py delete \
  --card "CRM - тестовая карточка" \
  --yes
```

## Mock mode for local testing

```bash
TASKCTL_MOCK=1 python taskctl.py list --list Today
```

Or set `TASKCTL_MOCK=1` in `.env`.
