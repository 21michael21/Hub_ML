---
title: Supervised Learning: Target, Features, Baseline
section: Classic ML
difficulty: medium
est_time: 45 мин
related_note: 03_ML/12_Supervised_Learning_Course_Article.md
links:
  - https://developers.google.com/machine-learning/crash-course
---

# Supervised Learning: Target, Features, Baseline

## Что сделать

Возьми сценарий conversion prediction: нужно предсказать, совершит ли пользователь заказ.

Опиши supervised learning задачу до написания модели:

1. Что является одной строкой датасета: пользователь, заказ, сессия или событие?
2. Как определить target `converted` через `df_orders.csv`?
3. Какие 5 простых features можно построить из `df_events.csv`?
4. Какие признаки могут быть leakage и почему?
5. Какой baseline ты построишь первым: rule-based, majority class или LogisticRegression?
6. Какие метрики покажешь: accuracy, precision, recall, F1, ROC AUC?

Не нужно сразу обучать сложную модель. Цель карточки — сделать постановку задачи понятной и проверяемой.

## Как себя проверить

- Target записан одной точной фразой.
- Features доступны до момента предсказания.
- Есть минимум два leakage риска.
- Baseline простой и объяснимый.
- Метрики выбраны под бизнес-смысл ошибок, а не "потому что так принято".
- Ты можешь объяснить разницу между classification и regression на этом примере.

## Что положить в портфолио

Мини-документ `supervised_baseline_plan.md`: target definition, feature list, leakage notes, split plan, baseline choice, metric choice, and one paragraph on limitations.
