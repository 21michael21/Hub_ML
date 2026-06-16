---
title: "Visualization: распределение комиссии"
section: Data Visualization
difficulty: easy
est_time: "30 мин"
dataset: "df_orders.csv"
links:
  - "https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html"
  - "https://seaborn.pydata.org/tutorial/distributions.html"
---

## Source

Mentor notebook: `content/source/vkat/VKAT-main/analysis_4_visualizations.ipynb`

Original assignment: “Задание 2: Гистограмма — Построй гистограмму распределения комиссии `commission` в датафрейме `df`. Поставь биновку 40 (`bins=40`).”

## Goal

Понять форму распределения комиссии: где находится основная масса заказов, есть ли длинный хвост, выбросы или необычные значения. Это помогает быстро увидеть, насколько стабильна комиссия и где могут быть аномалии.

## Dataset needed

`datasets/df_orders.csv`

Ключевая колонка:

- `commission`

## Task description

Загрузи `df_orders.csv` и построй histogram для `commission` с `bins=40`. После графика опиши форму распределения: симметричное оно или скошенное, где примерно основная масса значений, есть ли хвост или подозрительные выбросы.

## Suggested code starter

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("datasets/df_orders.csv")

fig, ax = plt.subplots(figsize=(9, 4))
ax.hist(df["commission"], bins=40, edgecolor="white", alpha=0.9)

# TODO: add title, axis labels, grid if useful, and interpretation.
plt.show()
```

## Visualization quality checklist

- Есть понятный title: что распределяется.
- Ось X подписана как комиссия, ось Y — как количество заказов.
- Бины читаемые: `bins=40` не превращает график в шум.
- Выбран корректный chart type: histogram для распределения числовой переменной.
- Есть полезный бизнес/аналитический insight: например, где типичный диапазон комиссии и есть ли хвост.
- Масштаб не вводит в заблуждение: выбросы не скрыты без объяснения.
- Есть portfolio-ready explanation: не только картинка, но и интерпретация.

## Self-review questions

- Где находится основной диапазон комиссии?
- Есть ли выбросы, которые стоит проверить отдельно?
- Нужно ли добавить вертикальную линию среднего или медианы?
- Не лучше ли для хвостатого распределения показать лог-шкалу или отдельный zoom-график?

## Portfolio artifact suggestion

Сохрани график и короткий текст: “Commission distribution: типичный диапазон, хвост, возможные аномалии”. Это можно положить как маленький EDA-блок в портфолио.
