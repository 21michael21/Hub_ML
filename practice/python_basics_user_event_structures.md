---
title: Python Basics: User Event Structures
section: Python
difficulty: easy
est_time: 35 мин
related_note: 01_Python/Core/03_Collections.md
links:
  - https://docs.python.org/3/tutorial/
---

# Python Basics: User Event Structures

## Что сделать

Потренируй базовые Python structures на маленьком списке пользовательских событий. Не используй pandas: цель этой карточки — почувствовать `list`, `dict`, `loop` и `function` руками.

Возьми список словарей:

```python
events = [
    {"user_id": 1, "event_type": "view", "price": 0},
    {"user_id": 1, "event_type": "purchase", "price": 1200},
    {"user_id": 2, "event_type": "view", "price": 0},
    {"user_id": 2, "event_type": "purchase", "price": 800},
]
```

Напиши функцию `summarize_user_events(events)`, которая возвращает словарь по `user_id`: сколько всего событий, сколько покупок и какая сумма покупок. Затем сделай маленький refactor: вынеси создание пустой записи пользователя в отдельную helper-функцию.

## Как себя проверить

- Функция не печатает результат, а возвращает обычный `dict`.
- В коде есть минимум два `assert` на ожидаемый результат.
- `view` увеличивает количество событий, но не увеличивает purchases и revenue.
- Код читается сверху вниз: данные, функция, вызов, проверки.
- Ты можешь словами объяснить, где используется `list`, где `dict`, где `loop`, а где `function`.

## Что положить в портфолио

Мини-артефакт "Plain Python event summary": код функции, 2-3 assert-проверки и короткое объяснение, как этот подход превращается в будущий pandas `groupby`.
