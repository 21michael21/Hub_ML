---
title: MLOps Monitoring: Data Drift Alert Plan
section: MLOps
difficulty: medium
est_time: 45 мин
related_note: 05_IT_Resources/MLOps/03_Model_Monitoring_Data_Drift.md
links:
  - https://madewithml.com/courses/mlops/
---

# MLOps Monitoring: Data Drift Alert Plan

## Что сделать

Спроектируй простой monitoring plan без Prometheus/Grafana и без внешних сервисов.

Сценарий: есть baseline conversion model, который использует `events_total`.

Даны:

```python
baseline_events_total = [2, 3, 2, 4, 3, 2]
current_events_total = [8, 7, 9, 8, 10, 7]
```

Сделай:

1. посчитай baseline mean и current mean;
2. задай simple alert condition, например `abs(delta) >= 3`;
3. напиши, что должно логироваться для каждой prediction;
4. опиши, что должен показывать monitoring dashboard;
5. напиши limitations: нет labels, маленький sample, mean не ловит все виды drift.

## Как себя проверить

- Есть baseline distribution и current distribution.
- Alert condition записан явно.
- Prediction log содержит timestamp, model_version, input summary, prediction, score.
- Dashboard показывает inputs, predictions, metrics over time, alerts.
- Есть human review loop: кто смотрит alert и что проверяет.
- Ты не называешь это production monitoring stack.

## Что положить в портфолио

`monitoring_plan.md`: drift check table, alert rule, prediction log schema, dashboard sketch, human review process, and limitations.
