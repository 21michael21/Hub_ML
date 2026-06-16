"""
БЛОК 7 — Паттерн: Рекурсия
============================
Запусти: python 07_recursion_pattern.py

СУТЬ ПАТТЕРНА:
  Функция вызывает саму себя с меньшим подзадачей.
  Каждый вызов — фрейм в call stack → O(глубина) памяти.

ЖЕЛЕЗНОЕ ПРАВИЛО: ВСЕГДА начинай с base case (условие выхода).
  Без base case → RecursionError (бесконечная рекурсия).

СТРУКТУРА ЛЮБОЙ РЕКУРСИВНОЙ ФУНКЦИИ:
  def solve(input):
      # 1. BASE CASE: самый маленький/пустой вход
      if base_condition:
          return base_value

      # 2. РЕКУРСИВНЫЙ ВЫЗОВ: уменьшаем задачу
      sub_result = solve(smaller_input)

      # 3. КОМБИНИРУЕМ: строим ответ из sub_result
      return combine(sub_result, current)

КАК СЧИТАТЬ СЛОЖНОСТЬ РЕКУРСИИ:
  Time = (число рекурсивных вызовов) × (работа на каждом)
  Space = глубина рекурсии (высота дерева вызовов)
"""

import sys

sys.setrecursionlimit(10_000)


# ─────────────────────────────────────────────
# БАЗОВЫЕ ПРИМЕРЫ — понимание call stack
# ─────────────────────────────────────────────


def factorial(n: int) -> int:
    """
    Time: O(n) — n вызовов.
    Space: O(n) — n фреймов в стеке.
    Base case: n == 0.
    """
    if n == 0:  # BASE CASE
        return 1
    return n * factorial(n - 1)  # рекурсивный вызов


def fibonacci_naive(n: int) -> int:
    """
    Time: O(2^n) — дерево вызовов удваивается на каждом уровне!
    Space: O(n) — глубина дерева.
    ЭТО ПЛОХО для больших n. Используй мемоизацию или итерацию.
    """
    if n <= 1:  # BASE CASE
        return n
    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)


def fibonacci_memo(n: int, memo: dict = None) -> int:
    """
    Time: O(n) с мемоизацией — каждое значение считается один раз.
    Space: O(n) — memo dict + call stack.
    """
    if memo is None:
        memo = {}
    if n <= 1:
        return n
    if n in memo:
        return memo[n]
    memo[n] = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 2, memo)
    return memo[n]


def fibonacci_iterative(n: int) -> int:
    """
    Time: O(n), Space: O(1) — лучший вариант.
    Рекурсию часто можно заменить итерацией.
    """
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


# ─────────────────────────────────────────────
# ЗАДАЧА 1: Climbing Stairs (Easy — LeetCode #70)
# ─────────────────────────────────────────────
# Условие: лестница из n ступенек. Можно прыгать на 1 или 2.
# Сколько различных способов добраться до вершины?
# Пример: n=3 → 3 (1+1+1, 1+2, 2+1)


def climb_stairs(n: int) -> int:
    """
    O(n) time, O(1) space — итеративно (Fibonacci!).

    ОБЪЯСНЕНИЕ:
      "Это Fibonacci: ways(n) = ways(n-1) + ways(n-2).
       С последнего шага: или пришли с n-1 (шаг 1), или с n-2 (шаг 2).
       Base cases: n=1 → 1 способ, n=2 → 2 способа."
    """
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(n - 2):
        a, b = b, a + b
    return b


def climb_stairs_recursive(n: int, memo: dict = None) -> int:
    """Рекурсивная версия с мемоизацией — O(n) time, O(n) space."""
    if memo is None:
        memo = {}
    if n <= 2:
        return n
    if n in memo:
        return memo[n]
    memo[n] = climb_stairs_recursive(n - 1, memo) + climb_stairs_recursive(n - 2, memo)
    return memo[n]


# ─────────────────────────────────────────────
# ЗАДАЧА 2: Merge Two Sorted Lists (Easy — LeetCode #21)
# ─────────────────────────────────────────────
# Условие: слить два отсортированных связных списка.


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

    def __repr__(self):
        vals = []
        curr = self
        while curr:
            vals.append(str(curr.val))
            curr = curr.next
        return " -> ".join(vals)


def merge_two_lists_recursive(l1: ListNode, l2: ListNode) -> ListNode:
    """
    O(n + m) time, O(n + m) space (call stack).

    ОБЪЯСНЕНИЕ:
      "Base case: если один из списков пуст — возвращаем другой.
       Иначе: берём меньший узел, его next = рекурсивный merge остатка."
    """
    if not l1:  # BASE CASE
        return l2
    if not l2:  # BASE CASE
        return l1
    if l1.val <= l2.val:
        l1.next = merge_two_lists_recursive(l1.next, l2)
        return l1
    else:
        l2.next = merge_two_lists_recursive(l1, l2.next)
        return l2


def merge_two_lists_iterative(l1: ListNode, l2: ListNode) -> ListNode:
    """
    O(n + m) time, O(1) space — итеративная версия.
    На интервью полезно показать оба варианта.
    """
    dummy = ListNode(0)
    curr = dummy
    while l1 and l2:
        if l1.val <= l2.val:
            curr.next = l1
            l1 = l1.next
        else:
            curr.next = l2
            l2 = l2.next
        curr = curr.next
    curr.next = l1 or l2
    return dummy.next


# ─────────────────────────────────────────────
# ЗАДАЧА 3: Invert Binary Tree (Easy — LeetCode #226)
# ─────────────────────────────────────────────


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def invert_tree(root: TreeNode) -> TreeNode:
    """
    O(n) time — посещаем каждый узел.
    O(h) space — h = высота дерева (call stack). O(log n) для сбалансированного.

    ОБЪЯСНЕНИЕ:
      "Base case: None → return None.
       Для каждого узла: меняем левое и правое поддерево местами,
       затем рекурсивно инвертируем каждое."
    """
    if not root:  # BASE CASE
        return None
    root.left, root.right = invert_tree(root.right), invert_tree(root.left)
    return root


# ─────────────────────────────────────────────
# ЗАДАЧА 4: Maximum Depth of Binary Tree (Easy — LeetCode #104)
# ─────────────────────────────────────────────


def max_depth(root: TreeNode) -> int:
    """
    O(n) time, O(h) space.
    Классический пример: глубина = 1 + max(глубина_левого, глубина_правого).
    """
    if not root:  # BASE CASE
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))


# ─────────────────────────────────────────────
# ЗАДАЧА 5: Power (Medium — LeetCode #50)
# ─────────────────────────────────────────────
# Реализуй pow(x, n). n может быть отрицательным.


def my_pow(x: float, n: int) -> float:
    """
    O(log n) time, O(log n) space.

    ОБЪЯСНЕНИЕ:
      "Fast power: x^n = x^(n//2) * x^(n//2) если n чётное.
       Это даёт O(log n) вместо O(n).
       Base case: n=0 → 1. Отрицательный n → 1/x^(-n)."
    """
    if n == 0:  # BASE CASE
        return 1.0
    if n < 0:
        return 1.0 / my_pow(x, -n)
    half = my_pow(x, n // 2)
    if n % 2 == 0:
        return half * half
    else:
        return half * half * x


# ─────────────────────────────────────────────
# ВИЗУАЛИЗАЦИЯ CALL STACK
# ─────────────────────────────────────────────


def visualize_call_stack():
    """Показывает, как выглядит call stack для factorial(4)."""
    print("═" * 50)
    print("КАК РАБОТАЕТ CALL STACK — factorial(4)")
    print("═" * 50)
    calls = [
        "factorial(4) → вызывает factorial(3)",
        "  factorial(3) → вызывает factorial(2)",
        "    factorial(2) → вызывает factorial(1)",
        "      factorial(1) → вызывает factorial(0)",
        "        factorial(0) → BASE CASE, возвращает 1",
        "      factorial(1) = 1 * 1 = 1, возвращает 1",
        "    factorial(2) = 2 * 1 = 2, возвращает 2",
        "  factorial(3) = 3 * 2 = 6, возвращает 6",
        "factorial(4) = 4 * 6 = 24, возвращает 24",
    ]
    for line in calls:
        print("  " + line)
    print()
    print("  Глубина = 5 (n+1) → Space O(n)")
    print("  Вызовов = 5 → Time O(n)")
    print()


# ─────────────────────────────────────────────
# ТЕСТЫ
# ─────────────────────────────────────────────


def make_list(*vals):
    if not vals:
        return None
    head = ListNode(vals[0])
    curr = head
    for v in vals[1:]:
        curr.next = ListNode(v)
        curr = curr.next
    return head


def list_to_arr(head):
    result = []
    while head:
        result.append(head.val)
        head = head.next
    return result


def run_tests():
    print("═" * 50)
    print("ТЕСТЫ — Рекурсия")
    print("═" * 50)

    assert factorial(0) == 1
    assert factorial(5) == 120
    print("  ✓ factorial")

    assert fibonacci_memo(0) == 0
    assert fibonacci_memo(10) == 55
    assert fibonacci_iterative(10) == 55
    print("  ✓ fibonacci")

    assert climb_stairs(1) == 1
    assert climb_stairs(2) == 2
    assert climb_stairs(3) == 3
    assert climb_stairs(5) == 8
    print("  ✓ climb_stairs")

    l1 = make_list(1, 2, 4)
    l2 = make_list(1, 3, 4)
    merged = merge_two_lists_recursive(l1, l2)
    assert list_to_arr(merged) == [1, 1, 2, 3, 4, 4]

    l1 = make_list(1, 2, 4)
    l2 = make_list(1, 3, 4)
    merged = merge_two_lists_iterative(l1, l2)
    assert list_to_arr(merged) == [1, 1, 2, 3, 4, 4]
    print("  ✓ merge_two_sorted_lists (recursive + iterative)")

    root = TreeNode(
        4, TreeNode(2, TreeNode(1), TreeNode(3)), TreeNode(7, TreeNode(6), TreeNode(9))
    )
    inverted = invert_tree(root)
    assert inverted.val == 4
    assert inverted.left.val == 7
    assert inverted.right.val == 2
    print("  ✓ invert_binary_tree")

    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))
    assert max_depth(root) == 3
    assert max_depth(None) == 0
    print("  ✓ max_depth")

    assert abs(my_pow(2.0, 10) - 1024.0) < 1e-9
    assert abs(my_pow(2.0, -2) - 0.25) < 1e-9
    print("  ✓ my_pow (fast exponentiation)")

    print("\nВсе тесты прошли!")


def show_complexity_summary():
    print("\n═" * 50)
    print("РЕЗЮМЕ СЛОЖНОСТЕЙ")
    print("═" * 50)
    tasks = [
        ("Factorial", "O(n) time, O(n) space", "линейная рекурсия, глубина = n"),
        ("Fibonacci naive", "O(2^n) time, O(n) space", "ПЛОХО — exponential!"),
        (
            "Fibonacci + memo",
            "O(n) time, O(n) space",
            "мемоизация устраняет дублирование",
        ),
        (
            "Climbing Stairs",
            "O(n) time, O(1) space",
            "это Fibonacci, решается итеративно",
        ),
        (
            "Merge Two Lists",
            "O(n+m) time, O(n+m) stack / O(1) iterative",
            "итеративная версия лучше по памяти",
        ),
        (
            "Invert Tree",
            "O(n) time, O(h) space",
            "h=log n для сбалансированного дерева",
        ),
        ("Max Depth Tree", "O(n) time, O(h) space", "1 + max(left, right)"),
        ("Fast Power", "O(log n) time, O(log n) space", "делим n пополам каждый раз"),
    ]
    for name, complexity, trick in tasks:
        print(f"  {name}:")
        print(f"    {complexity}")
        print(f"    Заметка: {trick}")
        print()


if __name__ == "__main__":
    visualize_call_stack()
    run_tests()
    show_complexity_summary()
