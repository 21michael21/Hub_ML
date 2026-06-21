---
title: Baseline Validation Metrics Drill
section: Classic ML
difficulty: medium
est_time: 40 мин
related_note: 03_ML/Validation/01_Validation_Metrics.md
links:
  - https://scikit-learn.org/stable/tutorial/index.html
---

# Baseline Validation Metrics Drill

## Что сделать

Возьми маленький binary classification пример и посчитай метрики вручную: confusion matrix, accuracy, precision, recall и F1.

```python
y_true = [1, 0, 1, 1, 0, 0, 1, 0]
y_pred = [1, 0, 1, 0, 0, 1, 1, 0]
```

Затем напиши короткий вывод: где модель ошиблась, что хуже для продукта в этом сценарии — false positive или false negative, и какую метрику ты бы выбрал для baseline report.

## Как себя проверить

- Ты явно посчитал TP, TN, FP, FN.
- Accuracy, precision, recall и F1 получились из этих counts.
- В выводе есть бизнес-интерпретация FP/FN, а не только формулы.
- Ты не называешь test score честным, если на нём подбирал решение.

## Что положить в портфолио

Мини-таблица "Baseline metrics": confusion matrix counts, 4 метрики и короткий абзац о tradeoff между precision и recall.
