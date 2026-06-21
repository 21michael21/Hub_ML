---
title: Python Typing Architecture Refactor
section: Python
difficulty: medium
est_time: 45 мин
related_note: 01_Python/Architecture/05_Typing_Architecture.md
links:
  - https://docs.python.org/3/tutorial/
---

# Python Typing Architecture Refactor

## Что сделать

Возьми маленький messy-фрагмент, где загрузка, очистка и расчёт результата смешаны в одной функции. Перепиши его как несколько typed functions с понятными signatures.

Стартовая идея:

```python
def process(rows):
    result = {}
    for row in rows:
        user = int(row["user_id"])
        amount = float(row.get("amount", 0))
        result[user] = result.get(user, 0) + amount
    print(result)
```

Сделай refactor:

- отдельная функция normalize row;
- отдельная функция aggregate by user;
- явные type hints на входах и выходах;
- dataclass или typed dict для нормализованной записи, если это делает код понятнее;
- без `print` внутри бизнес-логики: функция должна возвращать данные.

## Как себя проверить

- У каждой функции есть понятная signature.
- Каждая функция делает одну вещь.
- Возвращаемые значения стабильны: один тип результата, а не смесь `dict/list/None`.
- В коде есть 2-3 `assert` на поведение.
- Ты можешь объяснить module boundary: какие данные входят в модуль и какой результат выходит.

## Что положить в портфолио

Мини-раздел "Typed architecture refactor": messy-код до, clean-код после, короткая схема функций и объяснение, почему такой код легче тестировать в Data Lab или ML project.
