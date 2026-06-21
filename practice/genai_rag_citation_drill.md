---
title: RAG Retrieval Citation Drill
section: GenAI and RAG
difficulty: medium
est_time: 40 мин
related_note: 04_NLP/GenAI/03_RAG_Retrieval_Augmented_Generation.md
links:
  - https://www.promptingguide.ai/
---

# RAG Retrieval Citation Drill

## Что сделать

Это ручная RAG-практика без API, embeddings и vector DB.

Даны source snippets:

```text
S1: Hub_ML Practice cards are markdown files stored in practice/.
S2: Hub_ML Notebook uses a live Jupyter kernel to keep Python state between cells.
S3: Hub_ML Datasets tab previews CSV files from datasets/ and shows columns and describe().
```

Вопросы:

1. Where are practice cards stored?
2. What keeps Notebook variables alive between cells?
3. Does Hub_ML store practice cards in PostgreSQL?

Для каждого вопроса:

1. выбери самый релевантный snippet или напиши `unsupported`;
2. дай ответ только из выбранного snippet;
3. добавь citation вида `[S1]`;
4. если ответ не поддержан источниками, честно напиши: `Not supported by provided sources`.

## Как себя проверить

- Ответ на каждый supported question содержит citation.
- Unsupported question не превращён в догадку.
- Ты не добавил факты, которых нет в snippets.
- Ты можешь объяснить разницу между retrieval и generation.
- Ты перечислил минимум два failure modes: wrong chunk, missing source, stale source, unsupported answer.

## Что положить в портфолио

Мини-таблица `question / selected source / answer / support status`, плюс короткий раздел "RAG failure modes and citation policy".
