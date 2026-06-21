---
title: SQL SELECT JOIN Query Reading
section: SQL
difficulty: easy
est_time: 40 мин
related_note: 05_IT_Resources/SQL/SQL_Select_Join.md
dataset: df_orders.csv
links:
  - https://www.sqltutorial.org/
---

# SQL SELECT JOIN Query Reading

## Что сделать

Прочитай SQL-запрос и перепиши его локально через pandas `merge`.

SQL idea:

```sql
SELECT
    o.order_id,
    o.user_id,
    o.order_sum,
    m.exp_group
FROM orders AS o
INNER JOIN matching AS m
    ON o.user_id = m.user_id
WHERE o.order_sum > 10000;
```

В Notebook или Scratch:

1. Загрузи `datasets/df_orders.csv` и `datasets/df_matching.csv`.
2. Оставь из matching только `user_id` и `exp_group`.
3. Сделай pandas `merge` по `user_id`.
4. Отфильтруй строки, где `order_sum > 10000`.
5. Оставь только колонки из `SELECT`.
6. Запиши row count до join, после join и после фильтра.

## Как себя проверить

- Ты можешь объяснить, какая таблица является left/base table.
- Join key назван явно: `user_id`.
- В результате нет лишних колонок, которых не было в `SELECT`.
- Row count после inner join понятен и проверен.
- Ты можешь сказать, чем отличался бы `LEFT JOIN`.
- В коде нет абсолютных путей к данным.

## Что положить в портфолио

Мини-раздел "SQL query to pandas merge": SQL-запрос, pandas equivalent, таблица row counts и короткий вывод о том, почему join type важен для анализа.
