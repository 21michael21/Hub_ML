---
title: NumPy Matrix and Vector Scoring
section: Math for ML
difficulty: medium
est_time: 45 мин
related_note: 03_Ml/Math/01_Linear_Algebra_for_ML.md
dataset: df_orders.csv
links:
  - https://mml-book.com
---

# NumPy Matrix and Vector Scoring

## Что сделать

Построй маленький ML-style пример линейной алгебры на `datasets/df_orders.csv`.

Возьми первые 100 заказов, выбери числовые признаки `order_sum`, `commission`, `delivery_fee`, преврати их в NumPy matrix `X`, создай vector коэффициентов `w` и посчитай score через matrix-vector multiplication `X @ w`.

```python
import numpy as np
import pandas as pd

orders = pd.read_csv("datasets/df_orders.csv").head(100)
feature_columns = ["order_sum", "commission", "delivery_fee"]
X = orders[feature_columns].to_numpy(dtype=float)
w = np.array([0.001, 0.01, -0.002])
bias = 0.5

scores = X @ w + bias
print(X.shape, w.shape, scores.shape)
print(scores[:5])
```

Затем вручную проверь первый score через `np.dot(X[0], w) + bias` и сравни с `scores[0]`.

## Как себя проверить

- `X` имеет две размерности: rows = samples, columns = features.
- `w` имеет длину, равную числу колонок в `X`.
- `scores` имеет один score на строку `X`.
- Первый score из `X @ w + bias` совпадает с ручным `np.dot`.
- Ты можешь объяснить, почему `X * w` и `X @ w` отвечают на разные вопросы.

## Что положить в портфолио

Мини-раздел "Feature matrix sanity check": код, формы `X`, `w`, `scores`, ручная проверка первого dot product и короткое объяснение, почему такие проверки важны перед обучением ML-модели.
