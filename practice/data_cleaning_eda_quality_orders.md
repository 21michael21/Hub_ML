---
title: EDA Quality Missing Values Drill
section: Data Analysis
difficulty: easy
est_time: 40 мин
related_note: 02_Data_Analysis/EDA/01_Data_Cleaning_EDA.md
dataset: df_events.csv
links:
  - https://pandas.pydata.org/docs/user_guide/index.html
---

# EDA Quality Missing Values Drill

## Что сделать

Сделай первый data quality и EDA проход по `datasets/df_events.csv`.

Собери маленький отчёт:

- rows before cleaning;
- missing values by column;
- duplicate row count;
- rows after dropping duplicate rows and rows with missing `user_id`, `event_date`, `event_type`;
- event type distribution;
- date range.

Отдельно напиши, почему нельзя просто удалить все строки с missing `order_id`.

## Как себя проверить

- В отчёте есть row count before/after.
- Missing values считаются по каждой колонке.
- Required columns названы явно.
- Cleaning rule не удаляет полезные funnel events только потому, что у них нет `order_id`.
- Есть короткая caveats section для будущего EDA report.

## Что положить в портфолио

Мини-README "Event log quality checks": таблица missing values, duplicate count, event type counts, дата-диапазон и 3 вывода о качестве данных.
