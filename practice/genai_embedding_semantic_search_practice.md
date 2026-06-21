---
title: Embedding Semantic Search Drill
section: GenAI and RAG
difficulty: medium
est_time: 45 мин
related_note: 04_NLP/GenAI/02_Embedding_Vector_Search_Semantic_Search.md
links:
  - https://www.promptingguide.ai/
---

# Embedding Semantic Search Drill

## Что сделать

Собери маленький semantic search пример без API и без vector DB. Используй toy embedding vectors, чтобы понять механику поиска.

Создай 4 документа: `refund_policy`, `delivery_delay`, `account_security`, `promo_codes`. Для каждого задай NumPy vector вручную. Затем задай query vector и посчитай cosine similarity между query и каждым документом.

```python
import numpy as np

documents = {
    "refund_policy": np.array([1.0, 0.0, 0.0]),
    "delivery_delay": np.array([0.0, 1.0, 0.0]),
    "account_security": np.array([0.0, 0.0, 1.0]),
    "promo_codes": np.array([0.7, 0.2, 0.0]),
}
query = np.array([0.9, 0.1, 0.0])
```

Отсортируй документы по similarity и напиши короткое объяснение: почему top-1 победил, какой результат выглядит спорным, и что бы ты проверил перед подключением LLM.

## Как себя проверить

- У тебя есть функция cosine similarity.
- Результат возвращает ranked список, а не только один документ.
- В объяснении есть разница между semantic search и keyword search.
- Ты явно написал limitation: toy vectors не являются настоящими embeddings.
- Ты не используешь AI API, vector DB или RAG-фреймворк.

## Что положить в портфолио

Мини-ноутбук "Semantic search mechanics": код, таблица similarity scores, ranked results и короткий текст о рисках retrieval quality.
