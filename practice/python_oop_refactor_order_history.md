---
title: Python OOP Refactor: Order History Object
section: Python
difficulty: medium
est_time: 45 мин
related_note: 01_Python/OOP/08_Python_OOP_Class_Object.md
dataset: df_orders.csv
links:
  - https://docs.python.org/3/tutorial/
---

# Python OOP Refactor: Order History Object

## Что сделать

Возьми кусок логики, который работает со строками заказов, и оформи его как маленький object-oriented компонент.

Сделай class `UserOrderHistory`, который хранит `user_id` и список заказов. Добавь методы:

- `add_order(order_id, order_sum)`;
- `order_count`;
- `total_order_sum`;
- `average_order_sum`;
- `summary()`.

Проверь класс на пользователе `user_id == 2` из `datasets/df_orders.csv`.

## Как себя проверить

- Класс хранит состояние внутри объекта, а не в глобальных переменных.
- Два разных объекта можно создать для двух разных пользователей, и они не смешивают заказы.
- `summary()` возвращает обычный словарь, который удобно показать в notebook или README.
- В коде есть 2-3 assert на поведение класса.
- Ты можешь объяснить, почему здесь class лучше, чем набор несвязанных функций.

## Что положить в портфолио

Мини-раздел "OOP refactor for order history": короткое описание проблемы, код класса, тесты поведения и вывод о том, какие инварианты объект теперь защищает.
