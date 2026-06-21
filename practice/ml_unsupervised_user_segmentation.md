---
title: Unsupervised Learning: User Segmentation Sketch
section: Classic ML
difficulty: medium
est_time: 45 мин
related_note: 03_ML/14_Unsupervised_Learning_Course_Article.md
dataset: df_events.csv
links:
  - https://scikit-learn.org/stable/modules/clustering.html
---

# Unsupervised Learning: User Segmentation Sketch

## Что сделать

Построй черновой план user segmentation без обучения модели.

Используй `datasets/df_events.csv` и при необходимости посмотри `df_orders.csv`.

Сделай:

1. предложи 4-6 признаков для одной строки на `user_id`;
2. отметь, какие признаки нужно scaling перед clustering;
3. придумай 2-4 возможных сегмента пользователей;
4. объясни, почему эти сегменты являются гипотезами, а не истинными labels;
5. напиши, как бы ты проверил, что сегменты полезны для продукта.

Не добавляй clustering UI и не обещай автоматическую интерпретацию. Это ручная аналитическая практика.

## Как себя проверить

- Есть чёткое определение одной строки feature table.
- Есть признаки из событий, а не только из заказов.
- Ты отметил минимум один риск leakage или постфактум-интерпретации.
- Ты объяснил, почему scaling нужен для distance-based clustering.
- Для каждого сегмента есть осторожное, человеческое описание.
- В выводе есть limitations.

## Что положить в портфолио

Мини-раздел `User segmentation hypothesis`: feature list, expected clusters, scaling note, possible product actions, limitations, and next validation step.
