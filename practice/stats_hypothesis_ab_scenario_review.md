---
title: Statistics AB Test Hypothesis Confidence Interval Review
section: Statistics
difficulty: medium
est_time: 45 мин
related_note: 02_Data_Analysis/Stats/04_Hypothesis_AB_Testing.md
links:
  - https://experimentguide.com/
---

# Statistics AB Test Hypothesis Confidence Interval Review

## Что сделать

Разбери AB test scenario без тяжёлой статистики и без фейкового p-value. Отдельно напиши, где в полноценном анализе понадобился бы confidence interval, даже если в этой карточке ты его не считаешь.

Сценарий: команда изменила checkout page. В группе A конверсия `50 / 500`, в группе B конверсия `68 / 520`.

Сделай:

1. Запиши null hypothesis.
2. Запиши alternative hypothesis.
3. Назови unit of analysis и denominator.
4. Посчитай conversion rate для A и B.
5. Посчитай absolute uplift в percentage points.
6. Посчитай relative uplift.
7. Напиши решение: что можно сказать сейчас, а что нельзя.
8. Выпиши ограничения: sample size, peeking, multiple comparisons, guardrails.
9. Напиши, почему без confidence interval нельзя уверенно оценить диапазон возможного эффекта.

## Как себя проверить

- Null hypothesis формулируется как "нет реальной разницы".
- Alternative hypothesis говорит, какая разница ожидается.
- Denominator не смешивает users/events/orders.
- Effect size написан отдельно от вывода о статистической значимости.
- Ты не утверждаешь "B победил", если не считал uncertainty и не знаешь test plan.
- Ты явно написал, что confidence interval нужен для диапазона эффекта, а не для украшения отчёта.
- В решении есть next step: собрать больше данных, проверить guardrails или провести полноценный тест.

## Что положить в портфолио

Мини-readout: hypotheses, metric definition, rates table, effect size, limitations, and decision recommendation written in business language.
