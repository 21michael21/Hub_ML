---
title: NLP Vectorization: Bag of Words Baseline
section: NLP
difficulty: easy
est_time: 40 мин
related_note: 04_NLP/13_Text_Representations_Course_Article.md
links:
  - https://huggingface.co/learn/nlp-course/chapter1/1
---

# NLP Vectorization: Bag of Words Baseline

## Что сделать

Построй маленький bag-of-words baseline руками.

Используй документы:

```python
documents = [
    "good movie good acting",
    "bad movie slow plot",
    "good film strong plot",
]
```

Сделай:

1. простую tokenization через lower + split;
2. vocabulary в алфавитном порядке;
3. count vector для каждого документа;
4. сравнение двух документов по количеству общих ненулевых токенов;
5. короткий вывод: где bag-of-words помогает, а где ломается.

Не используй vector DB, embeddings или API. Это базовая text classifier / search practice перед более сложными representations.

## Как себя проверить

- Vocabulary один и тот же для всех документов.
- Count vectors имеют одинаковую длину.
- Ты можешь объяснить каждую колонку матрицы.
- В выводе есть limitation: порядок слов и синонимы теряются.
- Ты понимаешь, чем этот baseline отличается от embeddings.

## Что положить в портфолио

Мини-таблица: documents, vocabulary, count matrix, one similarity note, and limitations of bag-of-words.
