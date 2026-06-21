---
title: MLOps Experiment Log: Baseline Comparison
section: MLOps
difficulty: medium
est_time: 45 мин
related_note: 05_IT_Resources/MLOps/01_Experiment_Tracking.md
links:
  - https://madewithml.com/courses/mlops/
---

# MLOps Experiment Log: Baseline Comparison

## Что сделать

Заполни experiment log для двух baseline experiments. Можно использовать реальные результаты из Notebook или аккуратно описать imagined runs, но метрики нельзя выдумывать как факт.

Шаблон:

```markdown
| run_id | dataset | target | features | model | parameters | metric | notes |
|---|---|---|---|---|---|---|---|
| exp_001 | df_events + df_orders | converted | events_total | majority_baseline | strategy=most_frequent | real metric here | first baseline |
| exp_002 | df_events + df_orders | converted | events_total + event_type counts | logistic_regression | class_weight=balanced | real metric here | feature baseline |
```

Сделай:

1. выбери главную metric для сравнения;
2. напиши, какой run лучше и почему;
3. отметь, честное ли сравнение;
4. выпиши limitations;
5. добавь README paragraph для портфолио.

## Как себя проверить

- В log есть dataset, target, features, model, parameters, metric, notes.
- Метрики помечены как реальные или как placeholder, если ты ещё не запускал код.
- Ты не сравниваешь разные splits как одинаковые эксперименты.
- Есть limitation про leakage или data split.
- README paragraph объясняет не только лучший score, но и что изменилось между runs.

## Что положить в портфолио

`experiment_log.md`: таблица runs, comparison note, limitations, next experiment, and a short README section for the Classic ML baseline project.
