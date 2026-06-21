---
title: Python Algorithms: Hashmap Complexity Drill
section: Python
difficulty: medium
est_time: 45 мин
related_note: 01_Python/Algorithms/00_Algorithms_Map.md
links:
  - https://docs.python.org/3/tutorial/
---

# Python Algorithms: Hashmap Complexity Drill

## Что сделать

Реши маленькую livecoding-задачу через hashmap pattern и обязательно объясни complexity.

Задача: дан список строк `words`. Верни первый элемент, который встречается второй раз. Если повторов нет, верни `None`.

Starter code:

```python
def first_repeated_word(words: list[str]) -> str | None:
    # TODO: use a set or dict for seen words
    ...
```

Примеры:

```python
assert first_repeated_word(["red", "blue", "red"]) == "red"
assert first_repeated_word(["a", "b", "c"]) is None
assert first_repeated_word([]) is None
```

После решения напиши рядом:

- brute-force complexity;
- optimized complexity;
- почему `set` или `dict` подходит лучше, чем вложенный цикл;
- какие edge cases ты проверил.

## Как себя проверить

- Решение идёт одним проходом по списку.
- Нет вложенного цикла.
- Пустой список возвращает `None`.
- Первый повтор определяется по порядку просмотра, а не по алфавиту.
- В объяснении есть Big O time и memory.
- Ты можешь проговорить решение как на mock interview: clarify → brute force → optimized → tests.

## Что положить в портфолио

Один лог livecoding-паттерна: problem statement, hashmap cue, solution, asserts, complexity, edge cases, and a short explanation of why this is `O(n)`.
