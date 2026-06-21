---
title: NLP Transformer Pipeline Explainer
section: NLP
difficulty: medium
est_time: 45 мин
related_note: 04_NLP/12_Transformers_Course_Article.md
links:
  - https://huggingface.co/learn/nlp-course/chapter1/1
---

# NLP Transformer Pipeline Explainer

## Что сделать

Объясни transformer pipeline своими словами. Не запускай модели и не используй API.

Сделай короткий markdown-документ:

1. `raw text -> tokens -> embeddings -> attention -> output`;
2. что такое token и почему это не всегда слово;
3. что такое embedding на уровне интуиции;
4. что делает attention;
5. encoder-like use case: classification, NER, semantic search representation;
6. decoder-like use case: text generation, summary, chat answer;
7. почему LLM не является обычным search engine;
8. какие риски есть: hallucination, token limit, weak retrieval, prompt ambiguity.

Это conceptual NLP/LLM foundation перед будущим RAG Lab, а не реализация RAG.

## Как себя проверить

- Ты можешь объяснить pipeline без слов "магия" и без API.
- Есть разница между encoder-like и decoder-like задачами.
- Ты явно написал, что embeddings и LLM generation — не одно и то же.
- Есть список рисков и ограничений.
- Ты не обещаешь фактическую точность без retrieval/citations/evaluation.

## Что положить в портфолио

Одностраничный `transformer_pipeline_explainer.md`: схема pipeline, два use cases, limitations, and a short note on why future RAG needs retrieval plus evaluation.
