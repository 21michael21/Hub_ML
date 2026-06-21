---
title: MLOps Serving: Predict Function Contract
section: MLOps
difficulty: medium
est_time: 40 мин
related_note: 05_IT_Resources/MLOps/02_Model_Serving_Basics.md
links:
  - https://madewithml.com/courses/mlops/
---

# MLOps Serving: Predict Function Contract

## Что сделать

Напиши контракт для plain Python inference function без сервера.

Функция:

```python
predict_order_conversion(features: dict) -> dict
```

Опиши:

1. expected input dict: обязательные поля, типы, допустимые значения;
2. expected output dict: `prediction`, `score`, `model_version`;
3. как preprocessing должен совпадать с training;
4. чем batch prediction отличается от online inference;
5. три serving risks: training-serving skew, missing validation, hidden dependency, undocumented output.

Не добавляй FastAPI, Docker или cloud deployment. Это contract practice.

## Как себя проверить

- Input schema достаточно точная, чтобы другой человек мог вызвать функцию.
- Output schema содержит prediction, score, model_version.
- Есть explanation, что score означает.
- Есть минимум три serving risks.
- Ты явно написал, что API wrapper не исправляет плохой predict function.

## Что положить в портфолио

`serving_contract.md`: input schema, output schema, predict example, batch inference note, risks, and future API/Docker step marked as future work.
