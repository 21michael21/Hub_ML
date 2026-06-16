"""
БЛОК 1 — Big O: Time & Space Complexity
========================================
Запусти этот файл: python 01_big_o.py
Каждая функция сопровождена анализом сложности.
ЗАДАНИЕ: прежде чем читать комментарий — сам скажи вслух сложность.
"""

import time
import sys
from collections import deque


# ─────────────────────────────────────────────
# ЧАСТЬ 1: TIME COMPLEXITY — примеры для разбора
# ─────────────────────────────────────────────


def example_o1(arr):
    """
    Что делает: возвращает первый элемент.
    Time: O(1) — одна операция, не зависит от размера.
    Space: O(1) — ничего не создаём.
    """
    return arr[0]


def example_on(arr):
    """
    Что делает: суммирует элементы.
    Time: O(n) — один проход по массиву.
    Space: O(1) — только переменная total.
    """
    total = 0
    for x in arr:
        total += x
    return total


def example_on2(arr):
    """
    Что делает: ищет все пары.
    Time: O(n²) — вложенные циклы, каждый до n.
    Space: O(n²) — в худшем случае n² пар в результате.
    ПЛОХО для больших n. Типичная ситуация — перебор всех пар.
    """
    pairs = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            pairs.append((arr[i], arr[j]))
    return pairs


def example_ologn(arr, target):
    """
    Что делает: бинарный поиск в отсортированном массиве.
    Time: O(log n) — каждый шаг делим пространство поиска пополам.
    Space: O(1) — только несколько переменных.
    Запомни: если видишь "делим пополам" — это O(log n).
    """
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def example_onlogn(arr):
    """
    Что делает: сортирует массив.
    Time: O(n log n) — стандартная сортировка сравнением.
    Space: O(n) — Timsort (Python) создаёт временный массив.
    Запомни: sorted() и .sort() — всегда O(n log n).
    """
    return sorted(arr)


def example_on_dict(arr, target):
    """
    Что делает: ищет target через dict вместо вложенного цикла.
    Time: O(n) — один проход, lookup O(1).
    Space: O(n) — словарь хранит до n элементов.
    ВАЖНО: это оптимизация example_on2-подобного поиска!
    """
    seen = set()
    for x in arr:
        if target - x in seen:
            return True
        seen.add(x)
    return False


# ─────────────────────────────────────────────
# ЧАСТЬ 2: SPACE COMPLEXITY — примеры
# ─────────────────────────────────────────────


def space_o1_inplace(arr):
    """
    Space: O(1) — работаем in-place, никаких новых структур.
    Меняем элементы местами без доп. памяти.
    """
    l, r = 0, len(arr) - 1
    while l < r:
        arr[l], arr[r] = arr[r], arr[l]
        l += 1
        r -= 1
    return arr


def space_on_new_list(arr):
    """
    Space: O(n) — создаём новый список того же размера.
    Даже если алгоритм O(n) по времени — памяти тоже O(n).
    """
    result = []
    for x in arr:
        result.append(x * 2)
    return result


def space_recursion_on(n):
    """
    Space: O(n) — глубина стека вызовов равна n.
    Каждый рекурсивный вызов занимает память в call stack.
    Time: O(n) — n вызовов.
    """
    if n <= 0:
        return 0
    return n + space_recursion_on(n - 1)


def space_recursion_ologn(arr, lo, hi):
    """
    Space: O(log n) — глубина бинарного поиска log n.
    Рекурсивный бинарный поиск: делим пополам → log n фреймов стека.
    Time: O(log n).
    """
    if lo > hi:
        return -1
    mid = (lo + hi) // 2
    if arr[mid] == 0:
        return mid
    elif arr[mid] > 0:
        return space_recursion_ologn(arr, lo, mid - 1)
    else:
        return space_recursion_ologn(arr, mid + 1, hi)


# ─────────────────────────────────────────────
# ЧАСТЬ 3: УПРАЖНЕНИЯ — скажи вслух ДО проверки
# ─────────────────────────────────────────────


def exercise_1(arr):
    """ЗАДАНИЕ: какова Time и Space complexity? Скажи вслух, потом читай ответ."""
    result = {}
    for x in arr:
        if x not in result:
            result[x] = 0
        result[x] += 1
    return result
    # ОТВЕТ: Time O(n), Space O(n) — словарь до n уникальных ключей.


def exercise_2(matrix):
    """ЗАДАНИЕ: какова Time и Space complexity?"""
    total = 0
    for row in matrix:
        for val in row:
            total += val
    return total
    # ОТВЕТ: Time O(n*m) где n строк, m столбцов. Для квадратной — O(n²).
    #        Space O(1) — только счётчик.


def exercise_3(s):
    """ЗАДАНИЕ: какова Time и Space complexity?"""
    seen = set()
    for c in s:
        if c in seen:
            return False
        seen.add(c)
    return True
    # ОТВЕТ: Time O(n), Space O(min(n, alphabet)) — для ASCII = O(1), но формально O(n).


def exercise_4(arr):
    """ЗАДАНИЕ: какова Time и Space complexity?"""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return exercise_4(left) + mid + exercise_4(right)
    # ОТВЕТ: Это quicksort. Time O(n log n) среднее, O(n²) худшее.
    #        Space O(n log n) — новые списки на каждом уровне рекурсии.


def exercise_5(n):
    """ЗАДАНИЕ: какова Time и Space complexity? Есть ли проблема?"""
    result = []
    for i in range(n):
        result = result + [i]  # <— внимание на эту строку!
    return result
    # ОТВЕТ: Time O(n²)! result + [i] создаёт НОВЫЙ список каждый раз → O(1+2+...+n) = O(n²).
    #        Правильно: result.append(i) — тогда O(n).
    #        ML-разработчики часто делают эту ошибку в циклах!


# ─────────────────────────────────────────────
# ЧАСТЬ 4: ВИЗУАЛИЗАЦИЯ — наглядный рост
# ─────────────────────────────────────────────


def show_growth():
    """Показывает как растут O(1), O(log n), O(n), O(n²) при разных n."""
    import math

    ns = [1, 10, 100, 1000, 10000]
    print(
        f"\n{'n':>8} | {'O(1)':>6} | {'O(log n)':>10} | {'O(n)':>8} | {'O(n log n)':>12} | {'O(n²)':>10}"
    )
    print("-" * 70)
    for n in ns:
        logn = round(math.log2(n), 1)
        nlogn = round(n * math.log2(n))
        n2 = n * n
        print(f"{n:>8} | {'1':>6} | {logn:>10} | {n:>8} | {nlogn:>12} | {n2:>10}")
    print()
    print("Запомни: при n=10000 разница между O(n)=10k и O(n²)=100M огромная!")


if __name__ == "__main__":
    show_growth()

    print("\n=== ДЕМО: dict lookup vs list lookup ===")
    data_list = list(range(100_000))
    data_set = set(data_list)
    target = 99_999

    t0 = time.perf_counter()
    for _ in range(1000):
        _ = target in data_list
    list_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(1000):
        _ = target in data_set
    set_time = time.perf_counter() - t0

    print(f"  list (O(n)):  {list_time * 1000:.2f} ms")
    print(f"  set  (O(1)):  {set_time * 1000:.4f} ms")
    print(f"  Разница: {list_time / set_time:.0f}x — это и есть Big O в действии\n")

    print("=== УПРАЖНЕНИЯ — запусти и прочитай ответы в коде ===")
    print("  exercise_1: подсчёт частоты элементов")
    print("  exercise_2: сумма матрицы")
    print("  exercise_3: все символы уникальны?")
    print("  exercise_4: quicksort")
    print("  exercise_5: ЛОВУШКА — найди баг по сложности")
