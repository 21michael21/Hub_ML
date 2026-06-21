---
title: SQL Window Function Aggregation Drill
section: SQL
difficulty: medium
est_time: 45 мин
related_note: 05_IT_Resources/SQL/SQL_Aggregations_Windows.md
dataset: df_orders.csv
links:
  - https://www.practicewindowfunctions.com/
---

# SQL Window Function Aggregation Drill

## Что сделать

Отработай одну и ту же аналитику в двух формах: SQL-мышление и pandas-проверка.

Представь таблицу `orders` с колонками `order_id`, `user_id`, `event_date`, `order_sum`. Сначала напиши SQL-запрос, который считает по каждому пользователю количество заказов и сумму заказов через `GROUP BY`. Затем напиши второй запрос, который оставляет каждую строку заказа и добавляет:

- номер заказа пользователя через `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_date, order_id)`;
- накопительную сумму заказов пользователя через `SUM(order_sum) OVER (PARTITION BY user_id ORDER BY event_date, order_id)`.

После этого открой Notebook и повтори ту же идею в pandas на `datasets/df_orders.csv`.

```python
import pandas as pd

orders = pd.read_csv("datasets/df_orders.csv")
orders["event_date"] = pd.to_datetime(orders["event_date"])
orders = orders.sort_values(["user_id", "event_date", "order_id"])
orders["order_number_for_user"] = orders.groupby("user_id").cumcount() + 1
orders["running_order_sum_for_user"] = orders.groupby("user_id")["order_sum"].cumsum()

user_summary = (
    orders.groupby("user_id", as_index=False)
    .agg(orders_count=("order_id", "count"), total_order_sum=("order_sum", "sum"))
)
```

## Как себя проверить

- В SQL-части `GROUP BY` возвращает одну строку на пользователя, а window-запрос сохраняет одну строку на заказ.
- В window-запросе есть `PARTITION BY user_id` и явный `ORDER BY event_date, order_id`.
- В pandas `order_number_for_user` начинается с `1` внутри каждого пользователя.
- `running_order_sum_for_user` у пользователя никогда не уменьшается, если `order_sum` не отрицательный.
- Ты можешь словами объяснить, чем `GROUP BY` отличается от `SUM(...) OVER (...)`.

## Что положить в портфолио

Мини-README "SQL window features for order history": два SQL-запроса, pandas-проверка на `df_orders.csv`, маленькая таблица результата и 3-5 предложений о том, как такие признаки помогают продуктовой аналитике или baseline ML-модели.
