---
title: Feature Engineering: Build a Baseline Feature Table
section: Classic ML
difficulty: medium
est_time: 50 мин
related_note: 03_ML/07_Feature_Engineering.md
dataset: df_events.csv
links:
  - https://developers.google.com/machine-learning/crash-course
---

# Feature Engineering: Build a Baseline Feature Table

## Что сделать

Построй маленький feature table для baseline conversion model.

Используй `datasets/df_events.csv` и, если нужно, посмотри `df_orders.csv` / `df_matching.csv`.

Сделай:

1. одну строку на `user_id`;
2. `events_total`;
3. 2-4 признака-счётчика по `event_type`;
4. один признак, связанный с пропусками или отсутствием события;
5. список признаков, которые могут быть leakage;
6. короткое решение: какие признаки оставить для baseline, а какие исключить.

Не обучай модель в этой карточке. Фокус — качество feature table.

## Как себя проверить

- В таблице одна строка на пользователя.
- Каждый feature можно объяснить одной фразой.
- Есть минимум один numeric feature.
- Есть минимум один categorical/encoded или event-type feature.
- Leakage помечен явно, особенно всё, что напрямую связано с заказом после target moment.
- Ты проверил shape до и после merge/groupby.

## Что положить в портфолио

Раздел `Feature engineering`: таблица признаков, источник каждого признака, leakage note, missing-value strategy, and final baseline feature list.
