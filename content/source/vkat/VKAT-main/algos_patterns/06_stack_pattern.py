"""
БЛОК 6 — Паттерн: Stack
=========================
Запусти: python 06_stack_pattern.py

СУТЬ ПАТТЕРНА:
  Stack (стек) = список с операциями append() и pop() (LIFO).
  В Python: просто list, pop() без аргументов = O(1).

КОГДА ПРИМЕНЯТЬ — "красные флаги":
  - Задача про скобки, вложенность, пары → stack
  - "Следующий больший/меньший элемент" → monotonic stack
  - "Откат" / "предыдущее состояние" → stack
  - Рекурсию можно заменить на явный stack
  - "Обработай X, потом вернись к предыдущему состоянию"

СТРУКТУРА В PYTHON:
  stack = []
  stack.append(x)   # push  O(1)
  stack.pop()       # pop   O(1) — удаляет И возвращает последний
  stack[-1]         # peek  O(1) — смотрит без удаления
  not stack         # пустой?
"""


# ─────────────────────────────────────────────
# ЗАДАЧА 1: Valid Parentheses (Easy — LeetCode #20)
# ─────────────────────────────────────────────
# Условие: строка из '(', ')', '{', '}', '[', ']'.
# Является ли она валидной (скобки закрыты в правильном порядке)?
# Пример: "()[]{}" → True, "([)]" → False


def is_valid_parentheses(s: str) -> bool:
    """
    O(n) time, O(n) space.

    ОБЪЯСНЕНИЕ:
      "Открывающую скобку — кладём в стек.
       Закрывающую — проверяем: верхний стека = соответствующая открывающая?
       Если нет — невалидно. В конце стек должен быть пуст."
    """
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for c in s:
        if c in "([{":
            stack.append(c)
        elif not stack or stack[-1] != pairs[c]:
            return False
        else:
            stack.pop()
    return not stack


# ─────────────────────────────────────────────
# ЗАДАЧА 2: Daily Temperatures (Medium — LeetCode #739)
# ─────────────────────────────────────────────
# Условие: для каждого дня найти сколько дней ждать до более тёплого.
# Если такого нет — 0.
# Пример: [73,74,75,71,69,72,76,73] → [1,1,4,2,1,1,0,0]


def daily_temperatures(temperatures: list[int]) -> list[int]:
    """
    O(n) time, O(n) space — monotonic stack (убывающий).

    ОБЪЯСНЕНИЕ:
      "Monotonic stack: стек хранит индексы дней в порядке убывания температур.
       Когда находим день теплее чем стек[-1] — 'закрываем' все элементы стека
       которые меньше текущей температуры: для них ответ = current_idx - stack_idx."
    """
    result = [0] * len(temperatures)
    stack = []  # хранит индексы (температуры убывают сверху вниз)

    for i, temp in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < temp:
            j = stack.pop()
            result[j] = i - j
        stack.append(i)

    return result


# ─────────────────────────────────────────────
# ЗАДАЧА 3: Min Stack (Medium — LeetCode #155)
# ─────────────────────────────────────────────
# Условие: реализуй стек с O(1) для getMin().


class MinStack:
    """
    O(1) для всех операций.

    ОБЪЯСНЕНИЕ:
      "Храню два стека: основной и стек минимумов.
       При push: если новый элемент ≤ текущему минимуму — кладём и в min_stack.
       При pop: если удаляемый элемент == текущему минимуму — pop из обоих."
    """

    def __init__(self):
        self.stack = []
        self.min_stack = []  # всегда stack[-1] = текущий минимум

    def push(self, val: int) -> None:
        self.stack.append(val)
        min_val = val if not self.min_stack else min(val, self.min_stack[-1])
        self.min_stack.append(min_val)

    def pop(self) -> None:
        self.stack.pop()
        self.min_stack.pop()

    def top(self) -> int:
        return self.stack[-1]

    def get_min(self) -> int:
        return self.min_stack[-1]


# ─────────────────────────────────────────────
# ЗАДАЧА 4: Evaluate Reverse Polish Notation (Medium — LeetCode #150)
# ─────────────────────────────────────────────
# Условие: вычислить выражение в обратной польской нотации.
# Пример: ["2","1","+","3","*"] → 9   ((2+1)*3)


def eval_rpn(tokens: list[str]) -> int:
    """
    O(n) time, O(n) space.

    ОБЪЯСНЕНИЕ:
      "Классика стека: число — кладём в стек.
       Оператор — берём два числа из стека, вычисляем, кладём результат."
    """
    stack = []
    ops = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: int(a / b),  # int() truncates toward zero
    }
    for token in tokens:
        if token in ops:
            b, a = stack.pop(), stack.pop()
            stack.append(ops[token](a, b))
        else:
            stack.append(int(token))
    return stack[0]


# ─────────────────────────────────────────────
# ЗАДАЧА 5: Next Greater Element I (Easy — LeetCode #496)
# ─────────────────────────────────────────────
# Условие: для каждого элемента nums1 найти следующий больший в nums2.
# Если нет — -1.


def next_greater_element(nums1: list[int], nums2: list[int]) -> list[int]:
    """
    O(n + m) time, O(n) space — monotonic stack на nums2.

    ОБЪЯСНЕНИЕ:
      "Строю карту {элемент -> следующий больший} для nums2.
       Monotonic stack: держу элементы в убывающем порядке.
       Как только nums2[i] > stack[-1] — нашли следующий больший для stack[-1]."
    """
    next_greater = {}
    stack = []

    for num in nums2:
        while stack and stack[-1] < num:
            next_greater[stack.pop()] = num
        stack.append(num)

    while stack:
        next_greater[stack.pop()] = -1

    return [next_greater[x] for x in nums1]


# ─────────────────────────────────────────────
# БОНУС: когда стек заменяет рекурсию
# ─────────────────────────────────────────────


def binary_tree_inorder_iterative(root) -> list[int]:
    """
    In-order обход дерева без рекурсии — явный стек.
    Это важно знать: "как сделать рекурсивный алгоритм итеративным?"
    """
    result = []
    stack = []
    current = root

    while current or stack:
        while current:
            stack.append(current)
            current = current.left
        current = stack.pop()
        result.append(current.val)
        current = current.right

    return result


# ─────────────────────────────────────────────
# ТЕСТЫ
# ─────────────────────────────────────────────


def run_tests():
    print("═" * 50)
    print("ТЕСТЫ — Stack паттерн")
    print("═" * 50)

    assert is_valid_parentheses("()[]{}") is True
    assert is_valid_parentheses("([)]") is False
    assert is_valid_parentheses("{[]}") is True
    assert is_valid_parentheses("]") is False
    assert is_valid_parentheses("") is True
    print("  ✓ valid_parentheses")

    assert daily_temperatures([73, 74, 75, 71, 69, 72, 76, 73]) == [
        1,
        1,
        4,
        2,
        1,
        1,
        0,
        0,
    ]
    assert daily_temperatures([30, 40, 50, 60]) == [1, 1, 1, 0]
    assert daily_temperatures([30, 60, 90]) == [1, 1, 0]
    print("  ✓ daily_temperatures")

    ms = MinStack()
    ms.push(-2)
    ms.push(0)
    ms.push(-3)
    assert ms.get_min() == -3
    ms.pop()
    assert ms.top() == 0
    assert ms.get_min() == -2
    print("  ✓ MinStack")

    assert eval_rpn(["2", "1", "+", "3", "*"]) == 9
    assert eval_rpn(["4", "13", "5", "/", "+"]) == 6
    assert (
        eval_rpn(["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"])
        == 22
    )
    print("  ✓ eval_rpn")

    assert next_greater_element([4, 1, 2], [1, 3, 4, 2]) == [-1, 3, -1]
    assert next_greater_element([2, 4], [1, 2, 3, 4]) == [3, -1]
    print("  ✓ next_greater_element")

    print("\nВсе тесты прошли!")


def show_complexity_summary():
    print("\n═" * 50)
    print("РЕЗЮМЕ СЛОЖНОСТЕЙ")
    print("═" * 50)
    tasks = [
        (
            "Valid Parentheses",
            "O(n) time, O(n) space",
            "открывающие → в стек, закрывающие → проверяем",
        ),
        (
            "Daily Temperatures",
            "O(n) time, O(n) space",
            "monotonic stack убывающих температур",
        ),
        ("Min Stack", "O(1) всё, O(n) space", "параллельный стек минимумов"),
        (
            "Eval RPN",
            "O(n) time, O(n) space",
            "числа→стек, оператор→pop 2 числа→push результат",
        ),
        ("Next Greater Element", "O(n+m) time, O(n) space", "monotonic stack + dict"),
    ]
    for name, complexity, trick in tasks:
        print(f"  {name}:")
        print(f"    {complexity}")
        print(f"    Трюк: {trick}")
        print()

    print("КЛЮЧЕВЫЕ ФРАЗЫ для интервью:")
    print("  'Открывающую скобку кладём в стек, закрывающую сравниваем с вершиной'")
    print("  'Monotonic stack: держу элементы в порядке убывания'")
    print("  'stack[-1] — peek без удаления, O(1)'")


if __name__ == "__main__":
    run_tests()
    show_complexity_summary()
