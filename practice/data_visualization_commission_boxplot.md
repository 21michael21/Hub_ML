---
title: "Visualization: boxplot комиссии по стоимости доставки"
section: Data Visualization
difficulty: medium
est_time: "40 мин"
dataset: "df_orders.csv"
links:
  - "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.boxplot.html"
  - "https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.boxplot.html"
---

## Source

Mentor notebook: `content/source/vkat/VKAT-main/analysis_4_visualizations.ipynb`

Original assignment: “Задание 3: Boxplot — Построй Boxplot для комиссии (`commission`) в разрезе стоимости доставки (`delivery_fee`) с помощью Seaborn.”

## Goal

Сравнить распределение комиссии между группами заказов с разной стоимостью доставки. Boxplot помогает увидеть медиану, разброс, квартили и выбросы в каждой группе.

## Dataset needed

`datasets/df_orders.csv`

Ключевые колонки:

- `commission`
- `delivery_fee`

## Task description

Загрузи `df_orders.csv` и построй boxplot: по оси X — `delivery_fee`, по оси Y — `commission`. Отсортируй категории доставки, чтобы график читался последовательно. В оригинальном notebook это делается через Seaborn; здесь starter использует pandas/matplotlib, чтобы не добавлять новую зависимость.

После графика напиши вывод: отличается ли комиссия между группами доставки, где больше разброс, есть ли заметные выбросы.

## Suggested code starter

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("datasets/df_orders.csv")
delivery_order = sorted(df["delivery_fee"].dropna().unique())

fig, ax = plt.subplots(figsize=(8, 4))
df.boxplot(
    column="commission",
    by="delivery_fee",
    ax=ax,
    grid=False,
)
ax.set_title("Commission by delivery fee")
fig.suptitle("")

# TODO: add title, axis labels, readable category labels, and interpretation.
plt.show()
```

## Visualization quality checklist

- Есть понятный title: какая метрика сравнивается и по каким группам.
- Ось X подписана как стоимость доставки, ось Y — как комиссия.
- Категории доставки читаемы и отсортированы.
- Выбран корректный chart type: boxplot для сравнения распределений между категориями.
- Есть полезный бизнес/аналитический insight: где медиана/разброс/выбросы отличаются.
- Масштаб не вводит в заблуждение: выбросы видны или явно объяснены.
- Есть portfolio-ready explanation: вывод можно показать в EDA-отчёте.

## Self-review questions

- Какая группа доставки имеет самую высокую медианную комиссию?
- Где разброс комиссии шире всего?
- Похожи ли выбросы на реальные дорогие заказы или на ошибки данных?
- Нужен ли рядом countplot, чтобы понять размер каждой группы?

## Portfolio artifact suggestion

Сохрани график с выводом: “Commission by delivery fee: как стоимость доставки связана с комиссией”. Хороший портфолио-блок должен содержать не только boxplot, но и короткое объяснение, что это значит для продукта или монетизации.
