"""
БЛОК 3 — Паттерн: Hash Map
============================
Запусти: python 03_hashmap_pattern.py

СУТЬ ПАТТЕРНА:
  Когда нужно быстро (O(1)) проверить "видел ли я x раньше?"
  или "сколько раз встречался x?" — используй dict/set.
  Это превращает O(n²) в O(n).

КОГДА ПРИМЕНЯТЬ:
  - "Найди пару/тройку с суммой X"
  - "Есть ли дубликаты?"
  - "Сколько раз встречается каждый элемент?"
  - "Сгруппируй элементы по ключу"
  - "Найди первый неповторяющийся элемент"
"""

from collections import defaultdict, Counter


# ─────────────────────────────────────────────
# ШАБЛОНЫ — заучи структуру
# ─────────────────────────────────────────────


def template_seen_set(arr):
    """Шаблон 1: видел ли я этот элемент раньше?"""
    seen = set()
    for x in arr:
        if x in seen:
            # нашли дубликат / пару
            pass
        seen.add(x)


def template_count_freq(arr):
    """Шаблон 2: частота каждого элемента."""
    freq = {}
    for x in arr:
        freq[x] = freq.get(x, 0) + 1
    # или: freq = Counter(arr)
    return freq


def template_group_by_key(items, key_func):
    """Шаблон 3: сгруппировать по ключу."""
    groups = defaultdict(list)
    for item in items:
        groups[key_func(item)].append(item)
    return dict(groups)


def template_value_to_index(arr):
    """Шаблон 4: значение → индекс (или позиция), для быстрого поиска."""
    val_to_idx = {}
    for i, x in enumerate(arr):
        val_to_idx[x] = i
    return val_to_idx


# ─────────────────────────────────────────────
# ЗАДАЧА 1: Two Sum (Easy — LeetCode #1)
# ─────────────────────────────────────────────
# Условие: дан массив nums и число target.
# Найди индексы двух чисел, сумма которых равна target.
# Гарантировано ровно одно решение.
# Пример: nums=[2,7,11,15], target=9 → [0,1]


def two_sum_brute(nums: list[int], target: int) -> list[int]:
    """
    Brute force: O(n²) time, O(1) space.
    Перебираем все пары.
    """
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []


def two_sum(nums: list[int], target: int) -> list[int]:
    """
    Оптимально: O(n) time, O(n) space.
    Для каждого числа проверяем, есть ли его "дополнение" в seen.
    ОБЪЯСНЕНИЕ ДЛЯ ИНТЕРВЬЮ:
      "Вместо вложенного цикла — один проход.
       Храним в dict: {число -> индекс}.
       Для nums[i] нужна пара target - nums[i].
       Если она уже в seen — нашли!"
    """
    seen = {}  # value -> index
    for i, n in enumerate(nums):
        complement = target - n
        if complement in seen:
            return [seen[complement], i]
        seen[n] = i
    return []


# ─────────────────────────────────────────────
# ЗАДАЧА 2: Contains Duplicate (Easy — LeetCode #217)
# ─────────────────────────────────────────────
# Условие: есть ли в массиве хотя бы одно повторяющееся значение?


def contains_duplicate(nums: list[int]) -> bool:
    """
    O(n) time, O(n) space.
    Set хранит увиденные элементы → O(1) lookup.
    """
    seen = set()
    for n in nums:
        if n in seen:
            return True
        seen.add(n)
    return False
    # Однострочник: return len(nums) != len(set(nums))
    # Но однострочник не всегда уместен на интервью — покажи логику явно.


# ─────────────────────────────────────────────
# ЗАДАЧА 3: Group Anagrams (Medium — LeetCode #49)
# ─────────────────────────────────────────────
# Условие: сгруппировать строки, которые являются анаграммами друг друга.
# Пример: ["eat","tea","tan","ate","nat","bat"]
#       → [["bat"],["nat","tan"],["ate","eat","tea"]]


def group_anagrams(strs: list[str]) -> list[list[str]]:
    """
    O(n * k log k) time, где k — максимальная длина строки.
    O(n * k) space.

    КЛЮЧЕВАЯ ИДЕЯ: анаграммы имеют одинаковый ключ — отсортированная строка.
    "eat" -> "aet", "tea" -> "aet", "ate" -> "aet" — один ключ.

    ОБЪЯСНЕНИЕ ДЛЯ ИНТЕРВЬЮ:
      "Мне нужно группировать анаграммы. Ключ для группировки —
       отсортированная строка: все анаграммы дадут одинаковый ключ.
       Использую defaultdict(list): ключ -> список строк."
    """
    groups = defaultdict(list)
    for s in strs:
        key = tuple(sorted(s))  # "eat" -> ('a','e','t')
        groups[key].append(s)
    return list(groups.values())


# ─────────────────────────────────────────────
# ЗАДАЧА 4: Top K Frequent Elements (Medium — LeetCode #347)
# ─────────────────────────────────────────────
# Условие: найти k наиболее часто встречающихся элементов.
# Пример: nums=[1,1,1,2,2,3], k=2 → [1,2]


def top_k_frequent(nums: list[int], k: int) -> list[int]:
    """
    O(n log n) через сортировку, O(n) space.
    Есть решение O(n) через bucket sort, но для интервью достаточно этого.

    ОБЪЯСНЕНИЕ:
      "Считаю частоту через Counter. Потом беру k самых частых.
       most_common(k) внутри тоже O(n log n)."
    """
    freq = Counter(nums)
    return [item for item, _ in freq.most_common(k)]


def top_k_frequent_heap(nums: list[int], k: int) -> list[int]:
    """
    O(n log k) time через heap — быстрее при маленьком k.
    ОБЪЯСНЕНИЕ:
      "Вместо сортировки всего — поддерживаю heap размера k.
       heapq.nlargest(k, ...) делает это за нас."
    """
    import heapq

    freq = Counter(nums)
    return heapq.nlargest(k, freq.keys(), key=freq.get)


# ─────────────────────────────────────────────
# ЗАДАЧА 5: Valid Anagram (Easy — LeetCode #242)
# ─────────────────────────────────────────────
# Условие: являются ли строки s и t анаграммами?


def is_anagram(s: str, t: str) -> bool:
    """
    O(n) time, O(1) space (алфавит фиксирован).
    """
    if len(s) != len(t):
        return False
    return Counter(s) == Counter(t)
    # Альтернатива: return sorted(s) == sorted(t) — но O(n log n)


# ─────────────────────────────────────────────
# ЗАДАЧА 6: Longest Consecutive Sequence (Medium — LeetCode #128)
# ─────────────────────────────────────────────
# Условие: найти длину наидлиннейшей последовательности подряд идущих чисел.
# Пример: [100,4,200,1,3,2] → 4 (последовательность [1,2,3,4])
# Требование: O(n) time!


def longest_consecutive(nums: list[int]) -> int:
    """
    O(n) time, O(n) space.

    КЛЮЧЕВАЯ ИДЕЯ: начинаем последовательность только если нет num-1 в set.
    Это значит num — начало новой последовательности.
    Тогда считаем вперёд сколько можно.

    ОБЪЯСНЕНИЕ ДЛЯ ИНТЕРВЬЮ:
      "Конвертирую в set для O(1) lookup.
       Для каждого числа проверяю: если num-1 не в set, то это начало.
       Считаю, сколько подряд идут. Это O(n) суммарно —
       каждый элемент посещается не более двух раз."
    """
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


# ─────────────────────────────────────────────
# ТЕСТЫ
# ─────────────────────────────────────────────


def run_tests():
    print("═" * 50)
    print("ТЕСТЫ — Hash Map паттерн")
    print("═" * 50)

    # Two Sum
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]
    assert two_sum([3, 2, 4], 6) == [1, 2]
    assert two_sum([3, 3], 6) == [0, 1]
    print("  ✓ two_sum")

    # Contains Duplicate
    assert contains_duplicate([1, 2, 3, 1]) is True
    assert contains_duplicate([1, 2, 3, 4]) is False
    print("  ✓ contains_duplicate")

    # Group Anagrams
    result = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    result_sorted = sorted([sorted(g) for g in result])
    expected = sorted(
        [sorted(g) for g in [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]]]
    )
    assert result_sorted == expected
    print("  ✓ group_anagrams")

    # Top K Frequent
    assert set(top_k_frequent([1, 1, 1, 2, 2, 3], 2)) == {1, 2}
    assert top_k_frequent([1], 1) == [1]
    print("  ✓ top_k_frequent")

    # Is Anagram
    assert is_anagram("anagram", "nagaram") is True
    assert is_anagram("rat", "car") is False
    print("  ✓ is_anagram")

    # Longest Consecutive
    assert longest_consecutive([100, 4, 200, 1, 3, 2]) == 4
    assert longest_consecutive([0, 3, 7, 2, 5, 8, 4, 6, 0, 1]) == 9
    assert longest_consecutive([]) == 0
    print("  ✓ longest_consecutive")

    print("\nВсе тесты прошли!")


def show_complexity_summary():
    print("\n═" * 50)
    print("РЕЗЮМЕ СЛОЖНОСТЕЙ — скажи вслух для каждой")
    print("═" * 50)
    tasks = [
        ("Two Sum", "O(n) time, O(n) space", "один проход + dict"),
        ("Contains Duplicate", "O(n) time, O(n) space", "set для seen"),
        ("Group Anagrams", "O(n·k log k) time, O(n·k) space", "sorted tuple как ключ"),
        ("Top K Frequent", "O(n log k) time, O(n) space", "Counter + heap"),
        ("Valid Anagram", "O(n) time, O(1) space", "Counter сравнение"),
        ("Longest Consecutive", "O(n) time, O(n) space", "set + умный старт"),
    ]
    for name, complexity, trick in tasks:
        print(f"  {name}:")
        print(f"    {complexity}")
        print(f"    Трюк: {trick}")
        print()


if __name__ == "__main__":
    run_tests()
    show_complexity_summary()
