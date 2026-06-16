---
title: "Visualization: динамика суммы заказов по дням"
section: Data Visualization
difficulty: easy
est_time: "35 мин"
dataset: "df_orders.csv"
links:
  - "https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.plot.html"
  - "https://matplotlib.org/stable/gallery/ticks/date_formatters_locators.html"
---

## Source

Mentor notebook: `content/source/vkat/VKAT-main/analysis_4_visualizations.ipynb`

Original assignment: “Задание 1: Линейный график — Построй линейный график динамики суммы заказов по дням”.

## Goal

Построить линейный график, который показывает, как менялась суммарная выручка заказов по дням. Это базовый рабочий сценарий аналитика: увидеть тренд, пики, провалы и возможные даты для дальнейшего расследования.

## Dataset needed

`datasets/df_orders.csv`

Ключевые колонки:

- `event_date`
- `order_sum`

## Task description

Загрузи `df_orders.csv`, преобразуй `event_date` к datetime, сгруппируй заказы по дню и посчитай сумму `order_sum`. Построй line chart по датам.

После графика напиши 2–3 предложения: что видно по динамике, есть ли резкие изменения, какие даты стоит проверить глубже.

## Suggested code starter

```python
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

df = pd.read_csv("datasets/df_orders.csv")
df["event_date"] = pd.to_datetime(df["event_date"])

daily_revenue = (
    df.groupby("event_date", as_index=False)["order_sum"]
      .sum()
      .sort_values("event_date")
)

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(daily_revenue["event_date"], daily_revenue["order_sum"], marker="o")

# TODO: add title, axis labels, grid, date formatting, and short interpretation.
plt.show()
```

## Visualization quality checklist

- Есть понятный title: что именно показано и за какой уровень агрегации.
- Ось X подписана как дата, ось Y — как сумма заказов.
- Категории/даты читаемы: подписи не налезают друг на друга.
- Выбран корректный chart type: line chart для временного ряда.
- Есть полезный бизнес/аналитический insight, а не только “график построен”.
- Масштаб не вводит в заблуждение: нет случайного обрезания оси, которое драматизирует тренд.
- Есть portfolio-ready explanation: 2–3 предложения под графиком.

## Self-review questions

- Можно ли по графику быстро понять, в какие дни сумма заказов была выше или ниже обычного?
- Что может объяснить пики и провалы: сезонность, акции, сбои, изменение трафика?
- Нужно ли добавить скользящее среднее или аннотацию, чтобы график стал понятнее?
- Достаточно ли одного графика, или стоит рядом показать количество заказов по дням?

## Portfolio artifact suggestion

Сохрани notebook или markdown-отчёт с графиком, коротким выводом и списком следующих проверок. Хороший артефакт: “Daily revenue trend: что происходит с заказами по дням и какие даты требуют расследования”.
