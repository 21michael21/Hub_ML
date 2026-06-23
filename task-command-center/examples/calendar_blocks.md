# Calendar Blocks

Google Calendar должен отражать реальное время, а не все желания сразу.

## Deep work

```bash
python taskctl.py calendar \
  --title "CRM - login deep work" \
  --start "2026-06-18 10:00" \
  --end "2026-06-18 12:00" \
  --reminder 30
```

## Short reminder

```bash
python taskctl.py remind \
  --title "Проверить CRM login перед Done" \
  --at "2026-06-18 17:30" \
  --duration 15 \
  --reminder 10
```

## Review block

```bash
python taskctl.py calendar \
  --title "Review - CRM login PR" \
  --start "2026-06-19 11:00" \
  --end "2026-06-19 11:45" \
  --reminder 15
```

## Weekly Inbox cleanup

```bash
python taskctl.py calendar \
  --title "Command Center - Inbox cleanup" \
  --start "2026-06-21 18:00" \
  --end "2026-06-21 18:30" \
  --reminder 30
```
