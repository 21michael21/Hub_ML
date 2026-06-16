"""
БЛОК 8 — Mock Interview
=========================
Запусти: python 08_mock_interview.py

ИНСТРУКЦИЯ:
  Это симуляция реального интервью. Для каждой задачи:
  1. Прочитай условие — ЗАКРОЙ решение ниже
  2. Вслух скажи: "Я понял задачу так: ..."
  3. Вслух предложи brute force и его сложность
  4. Вслух предложи оптимизацию
  5. Пишешь код — КОММЕНТИРУЙ каждый шаг вслух
  6. После кода: назови time/space complexity
  7. Проверь на примере из условия вручную
  8. Проверь edge cases: [], [1], все одинаковые

  Таймер: 35-40 минут на задачу (включая объяснение).
  Если застрял на 10 минут — разрешается посмотреть подсказку.

ЗАДАЧИ:
  MOCK 1: Product of Array Except Self    (Medium)
  MOCK 2: Longest Consecutive Sequence    (Medium) — уже в 03, но реши сам!
  MOCK 3: Find Minimum in Rotated Array   (Medium)
"""

# ═══════════════════════════════════════════════
# MOCK 1: Product of Array Except Self (Medium — LeetCode #238)
# ═══════════════════════════════════════════════
"""
УСЛОВИЕ:
  Дан массив nums. Вернуть массив output где output[i] =
  произведение всех элементов nums КРОМЕ nums[i].
  Решить за O(n), БЕЗ деления!

ПРИМЕР:
  Input:  [1, 2, 3, 4]
  Output: [24, 12, 8, 6]
         (2*3*4, 1*3*4, 1*2*4, 1*2*3)

EDGE CASES:
  - nums = [0, 1]  → [1, 0]
  - nums = [0, 0]  → [0, 0]
  - nums = [-1, 1, 0, -3, 3]

ВОПРОСЫ ДЛЯ ИНТЕРВЬЮЕРА:
  - Гарантировано ли, что len(nums) >= 2? (обычно да)
  - Могут ли быть нули? (да)

ПОДСКАЗКА (не читай сразу!):
  Раздели на два прохода: слева-направо и справа-налево.
  prefix[i] = произведение всех элементов слева от i.
  suffix[i] = произведение всех элементов справа от i.
  output[i] = prefix[i] * suffix[i].
"""


def product_except_self_brute(nums: list[int]) -> list[int]:
    """
    BRUTE FORCE: O(n²) time, O(1) space (не считая output).
    Для понимания — назови это интервьюеру как стартовую точку.
    """
    n = len(nums)
    output = []
    for i in range(n):
        product = 1
        for j in range(n):
            if j != i:
                product *= nums[j]
        output.append(product)
    return output


def product_except_self(nums: list[int]) -> list[int]:
    """
    ОПТИМАЛЬНО: O(n) time, O(1) extra space (output не считается).

    АЛГОРИТМ:
      1. Левый проход: output[i] = произведение всего левее i
         output[0]=1, output[1]=nums[0], output[2]=nums[0]*nums[1], ...
      2. Правый проход: умножаем на суффиксное произведение
         Идём справа, накапливаем suffix, умножаем output[i] *= suffix
    """
    n = len(nums)
    output = [1] * n

    # Левый проход: prefix
    prefix = 1
    for i in range(n):
        output[i] = prefix
        prefix *= nums[i]

    # Правый проход: умножаем на suffix
    suffix = 1
    for i in range(n - 1, -1, -1):
        output[i] *= suffix
        suffix *= nums[i]

    return output


# ═══════════════════════════════════════════════
# MOCK 2: Longest Consecutive Sequence (Medium — LeetCode #128)
# ═══════════════════════════════════════════════
"""
УСЛОВИЕ:
  Дан неотсортированный массив nums. Найти длину наидлиннейшей
  последовательности подряд идущих чисел.
  Решить за O(n)!

ПРИМЕР:
  Input:  [100, 4, 200, 1, 3, 2]
  Output: 4   (последовательность [1, 2, 3, 4])

EDGE CASES:
  - [] → 0
  - [1] → 1
  - [1, 1, 1] → 1 (дубликаты)

ЛОВУШКА: сортировка даёт O(n log n) — не подходит!

ПОДСКАЗКА:
  Конвертируй в set. Для числа n начинай считать последовательность
  только если n-1 НЕТ в set (n — начало последовательности).
"""


def longest_consecutive(nums: list[int]) -> int:
    """O(n) time, O(n) space."""
    num_set = set(nums)
    best = 0

    for num in num_set:
        if num - 1 not in num_set:  # num — начало последовательности
            current = num
            streak = 1
            while current + 1 in num_set:
                current += 1
                streak += 1
            best = max(best, streak)

    return best


# ═══════════════════════════════════════════════
# MOCK 3: Find Minimum in Rotated Sorted Array (Medium — LeetCode #153)
# ═══════════════════════════════════════════════
"""
УСЛОВИЕ:
  Изначально отсортированный массив был "ротирован" (сдвинут).
  Например: [3,4,5,1,2] (ротация [1,2,3,4,5]).
  Найти минимальный элемент за O(log n).

ПРИМЕР:
  [3,4,5,1,2] → 1
  [4,5,6,7,0,1,2] → 0
  [11,13,15,17] → 11 (не ротирован)

EDGE CASES:
  - Массив не ротирован → минимум = arr[0]
  - Один элемент

ПОДСКАЗКА:
  Бинарный поиск. Сравнивай arr[mid] с arr[r].
  Если arr[mid] > arr[r] — минимум в правой половине.
  Иначе — в левой (включая mid).
"""


def find_min(nums: list[int]) -> int:
    """
    O(log n) time, O(1) space — binary search.

    КЛЮЧЕВОЙ ИНСАЙТ:
      В ротированном массиве одна из половин всегда отсортирована.
      Если arr[mid] > arr[r]: точка ротации (минимум) в правой половине.
      Если arr[mid] <= arr[r]: минимум в левой половине (включая mid).
    """
    l, r = 0, len(nums) - 1

    while l < r:
        mid = (l + r) // 2
        if nums[mid] > nums[r]:
            l = mid + 1  # минимум в правой половине
        else:
            r = mid  # минимум в левой половине (mid может быть ответом!)

    return nums[l]


# ═══════════════════════════════════════════════
# ТЕСТЫ + ПОДРОБНЫЙ РАЗБОР РЕШЕНИЙ
# ═══════════════════════════════════════════════


def run_tests():
    print("═" * 50)
    print("ТЕСТЫ — Mock Interview задачи")
    print("═" * 50)

    assert product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]
    assert product_except_self([0, 1]) == [1, 0]
    assert product_except_self([-1, 1, 0, -3, 3]) == [0, 0, 9, 0, 0]
    assert product_except_self_brute([1, 2, 3, 4]) == [24, 12, 8, 6]
    print("  ✓ product_except_self")

    assert longest_consecutive([100, 4, 200, 1, 3, 2]) == 4
    assert longest_consecutive([0, 3, 7, 2, 5, 8, 4, 6, 0, 1]) == 9
    assert longest_consecutive([]) == 0
    assert longest_consecutive([1, 1, 1]) == 1
    print("  ✓ longest_consecutive")

    assert find_min([3, 4, 5, 1, 2]) == 1
    assert find_min([4, 5, 6, 7, 0, 1, 2]) == 0
    assert find_min([11, 13, 15, 17]) == 11
    assert find_min([1]) == 1
    assert find_min([2, 1]) == 1
    print("  ✓ find_min (rotated sorted array)")

    print("\nВсе тесты прошли!")


def show_mock_walkthroughs():
    """Пошаговый разбор решений — прочитай ПОСЛЕ того как сам попробовал."""
    print("\n═" * 50)
    print("РАЗБОР РЕШЕНИЙ")
    print("═" * 50)

    print("""
MOCK 1: Product Except Self
  Brute: O(n²) — два вложенных цикла.
  Оптимум: O(n) — два прохода, prefix и suffix.
    Шаг 1: output[i] = произведение всего СЛЕВА от i
           i=0: output[0]=1 (слева ничего)
           i=1: output[1]=nums[0]=1
           i=2: output[2]=1*2=2
           i=3: output[3]=1*2*3=6
    Шаг 2: умножаем suffix справа налево
           i=3: output[3]*=1=6,   suffix*=4 → suffix=4
           i=2: output[2]*=4=8,   suffix*=3 → suffix=12
           i=1: output[1]*=12=12, suffix*=2 → suffix=24
           i=0: output[0]*=24=24, suffix*=1
    Результат: [24, 12, 8, 6] ✓

MOCK 2: Longest Consecutive
  Brute: O(n²) или O(n log n) через сортировку.
  Оптимум: O(n) — set + умный старт.
    Ключ: начинаем считать ТОЛЬКО если num-1 не в set.
    Это значит num — начало последовательности.
    Каждый элемент посещается максимум 2 раза → O(n).

MOCK 3: Find Minimum in Rotated Array
  Brute: O(n) — линейный поиск.
  Оптимум: O(log n) — binary search.
    [3,4,5,|1,2]: mid=5 > r=2 → минимум правее → l=mid+1
    [3,4,5,1,|2]: это не правильно, давай ещё раз:
    l=0, r=4, mid=2: nums[2]=5 > nums[4]=2 → l=3
    l=3, r=4, mid=3: nums[3]=1 <= nums[4]=2 → r=3
    l==r → return nums[3] = 1 ✓
""")


def show_complexity_summary():
    print("═" * 50)
    print("РЕЗЮМЕ МОКА")
    print("═" * 50)
    tasks = [
        (
            "Product Except Self",
            "O(n) time, O(1) extra space",
            "prefix + suffix за два прохода",
        ),
        (
            "Longest Consecutive",
            "O(n) time, O(n) space",
            "set + старт только с num-1 ∉ set",
        ),
        ("Find Min Rotated", "O(log n) time, O(1) space", "binary search: mid vs r"),
    ]
    for name, complexity, trick in tasks:
        print(f"  {name}:")
        print(f"    {complexity}")
        print(f"    Трюк: {trick}")
        print()


if __name__ == "__main__":
    run_tests()
    show_mock_walkthroughs()
    show_complexity_summary()
