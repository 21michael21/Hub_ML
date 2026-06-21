---
title: NLP Preprocessing: Clean Interview and User Messages
section: NLP
difficulty: easy
est_time: 35 мин
related_note: 04_NLP/02_Text_Preprocessing.md
links:
  - https://huggingface.co/learn/nlp-course/chapter1/1
---

# NLP Preprocessing: Clean Interview and User Messages

## Что сделать

Это cleaning-практика перед простым text classifier или search baseline: ты сравниваешь сырой текст, очищенный текст и токены.

Возьми маленький список сообщений:

```python
messages = [
    "Great work!!! Can you send the README?",
    "I can't open the dataset: https://example.com/data",
    "NOT happy with this answer...",
    "Order #123 failed twice :(",
]
```

Сделай простую preprocessing-функцию на стандартной библиотеке:

1. lowercasing;
2. обработка URL;
3. аккуратная punctuation handling;
4. tokenization через `split()` после нормализации;
5. таблица raw text / cleaned text / tokens;
6. короткий вывод: какую информацию preprocessing потерял.

Не используй transformers, API или внешние NLP-библиотеки. Цель — понять text pipeline руками.

## Как себя проверить

- У тебя есть raw и cleaned версия каждого сообщения.
- Token list не содержит пустых строк.
- Ты явно написал, что потерялось: эмоция, пунктуация, номер заказа, ссылка или регистр.
- Ты объяснил, почему preprocessing зависит от задачи.
- Ты не называешь stop-word removal обязательным шагом.

## Что положить в портфолио

Мини-таблица `raw -> cleaned -> tokens` и один абзац: "Preprocessing decisions and information loss".
