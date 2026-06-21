---
title: Math Optimization: Quadratic Gradient Descent
section: Math for ML
difficulty: medium
est_time: 40 мин
related_note: 03_ML/Math/02_Optimization_Basics.md
links:
  - https://mml-book.com
---

# Math Optimization: Quadratic Gradient Descent

## Что сделать

Минимизируй простую функцию:

```python
f(x) = (x - 3) ** 2
```

Напиши:

1. функцию `loss(x)`;
2. функцию `gradient(x)`;
3. цикл из 10 шагов gradient descent;
4. список `loss_history`;
5. эксперимент с двумя learning rates: например `0.05` и `0.5`.

Опиши, как learning rate меняет скорость и стабильность движения к минимуму.

## Как себя проверить

- Финальный `x` стал ближе к `3`, чем начальный.
- Loss уменьшился по сравнению с первым шагом.
- Ты можешь объяснить, почему шаг выглядит как `x = x - learning_rate * gradient(x)`.
- Есть 2-3 наблюдения про learning rate.
- Ты не называешь этот пример "обучением модели", а используешь его как интуицию перед ML training.

## Что положить в портфолио

Короткий notebook fragment: формула loss, update rule, таблица `step / x / loss`, график loss history или текстовое описание, и вывод о learning rate.
