"""
БЛОК 5 — Паттерн: Sliding Window
==================================
Запусти: python 05_sliding_window_pattern.py

СУТЬ ПАТТЕРНА:
  Поддерживаем "окно" (подмассив/подстроку) между указателями l и r.
  Двигаем r вправо чтобы расширить, l вправо чтобы сузить.
  Это позволяет решать задачи о подмассивах за O(n) вместо O(n²) или O(n³).

ДВА ВАРИАНТА:
  1. Фиксированная ширина: окно всегда = k
     → "среднее/сумма/max подмассива длиной k"
  2. Переменная ширина: расширяем пока можем, сужаем когда нарушается условие
     → "наидлиннейшая/наикратчайшая подстрока с условием"

КОГДА ПРИМЕНЯТЬ:
  - "Найди наидлиннейшую подстроку без повторений"
  - "Минимальный подмассив с суммой ≥ target"
  - "Максимальная сумма подмассива длиной k"
  - "Содержит ли s2 перестановку s1?"
"""

from collections import defaultdict


# ─────────────────────────────────────────────
# ШАБЛОНЫ — заучи структуру
# ─────────────────────────────────────────────


def template_fixed_window(arr, k):
    """Шаблон 1: фиксированное окно размера k."""
    if len(arr) < k:
        return []

    window_sum = sum(arr[:k])
    result = [window_sum]

    for r in range(k, len(arr)):
        window_sum += arr[r]  # добавляем правый элемент
        window_sum -= arr[r - k]  # убираем крайний левый
        result.append(window_sum)

    return result


def template_variable_window(s):
    """Шаблон 2: переменное окно, расширяем/сужаем по условию."""
    l = 0
    state = {}  # состояние окна (например, счётчик символов)
    best = 0

    for r in range(len(s)):
        # 1. Добавляем s[r] в состояние окна
        # state[s[r]] = state.get(s[r], 0) + 1

        # 2. Пока окно нарушает условие — сужаем слева
        # while <нарушено условие>:
        #     state[s[l]] -= 1
        #     l += 1

        # 3. Обновляем результат
        best = max(best, r - l + 1)

    return best


# ─────────────────────────────────────────────
# ЗАДАЧА 1: Best Time to Buy and Sell Stock (Easy — LeetCode #121)
# ─────────────────────────────────────────────
# Условие: массив цен акций по дням. Купить в один день, продать в другой позже.
# Найти максимальную прибыль.
# Пример: [7,1,5,3,6,4] → 5 (купить за 1, продать за 6)


def max_profit(prices: list[int]) -> int:
    """
    O(n) time, O(1) space.
    Это по сути sliding window: l=день покупки, r=день продажи.

    ОБЪЯСНЕНИЕ:
      "l — день покупки (минимальная цена видённая слева).
       r — день продажи (текущий день).
       Если текущая цена < цены покупки — обновляем l (нашли лучший день покупки).
       Иначе — считаем прибыль."
    """
    if not prices:
        return 0
    buy = prices[0]
    profit = 0
    for price in prices[1:]:
        if price < buy:
            buy = price
        else:
            profit = max(profit, price - buy)
    return profit


# ─────────────────────────────────────────────
# ЗАДАЧА 2: Longest Substring Without Repeating Characters (Medium — LeetCode #3)
# ─────────────────────────────────────────────
# Условие: найти длину наидлиннейшей подстроки без повторяющихся символов.
# Пример: "abcabcbb" → 3 ("abc")


def length_of_longest_substring(s: str) -> int:
    """
    O(n) time, O(min(n, 128)) space — переменное окно.

    ОБЪЯСНЕНИЕ:
      "Поддерживаю окно [l..r] без повторений.
       Когда добавляю s[r] и он уже в окне — двигаю l до позиции после
       предыдущего вхождения s[r], чтобы устранить повторение.
       Храню {символ -> последний индекс} для O(1) доступа."
    """
    seen = {}  # char -> last index
    l = res = 0
    for r, c in enumerate(s):
        if c in seen and seen[c] >= l:
            l = seen[c] + 1  # двигаем l чтобы убрать дубль
        seen[c] = r
        res = max(res, r - l + 1)
    return res


# ─────────────────────────────────────────────
# ЗАДАЧА 3: Permutation in String (Medium — LeetCode #567)
# ─────────────────────────────────────────────
# Условие: содержит ли s2 подстроку, являющуюся перестановкой s1?
# Пример: s1="ab", s2="eidbaooo" → True (подстрока "ba")


def check_inclusion(s1: str, s2: str) -> bool:
    """
    O(n) time, O(1) space (26 букв = константа).
    Фиксированное окно размера len(s1).

    ОБЪЯСНЕНИЕ:
      "Окно фиксированной ширины = len(s1).
       Сравниваю частоту символов в окне с частотой в s1.
       Когда matches == 26 — нашли перестановку."
    """
    if len(s1) > len(s2):
        return False

    s1_count = [0] * 26
    window_count = [0] * 26

    for c in s1:
        s1_count[ord(c) - ord("a")] += 1
    for c in s2[: len(s1)]:
        window_count[ord(c) - ord("a")] += 1

    matches = sum(1 for i in range(26) if s1_count[i] == window_count[i])

    for r in range(len(s1), len(s2)):
        if matches == 26:
            return True

        # добавляем правый символ
        idx_r = ord(s2[r]) - ord("a")
        if window_count[idx_r] == s1_count[idx_r]:
            matches -= 1
        window_count[idx_r] += 1
        if window_count[idx_r] == s1_count[idx_r]:
            matches += 1

        # убираем крайний левый символ
        idx_l = ord(s2[r - len(s1)]) - ord("a")
        if window_count[idx_l] == s1_count[idx_l]:
            matches -= 1
        window_count[idx_l] -= 1
        if window_count[idx_l] == s1_count[idx_l]:
            matches += 1

    return matches == 26


# ─────────────────────────────────────────────
# ЗАДАЧА 4: Minimum Window Substring (Hard — LeetCode #76)
# ─────────────────────────────────────────────
# Условие: найти минимальную подстроку s, содержащую все символы t.
# Пример: s="ADOBECODEBANC", t="ABC" → "BANC"
# (Hard, но паттерн важен — переменное окно с условием "contains all")


def min_window(s: str, t: str) -> str:
    """
    O(n + m) time, O(n + m) space.

    ОБЪЯСНЕНИЕ:
      "Переменное окно. Расширяю r пока не соберу все символы t.
       Затем сужаю l пока окно ещё валидно — ищу минимум.
       Отслеживаю 'have' (сколько уникальных символов t в окне в нужном кол-ве)
       vs 'need' (сколько уникальных символов в t)."
    """
    if not t or not s:
        return ""

    need = defaultdict(int)
    for c in t:
        need[c] += 1

    have_count = defaultdict(int)
    have = 0
    total_need = len(need)

    result = ""
    result_len = float("inf")
    l = 0

    for r, c in enumerate(s):
        have_count[c] += 1
        if c in need and have_count[c] == need[c]:
            have += 1

        while have == total_need:
            # обновляем результат
            if (r - l + 1) < result_len:
                result_len = r - l + 1
                result = s[l : r + 1]
            # сужаем окно слева
            have_count[s[l]] -= 1
            if s[l] in need and have_count[s[l]] < need[s[l]]:
                have -= 1
            l += 1

    return result


# ─────────────────────────────────────────────
# ЗАДАЧА 5: Maximum Average Subarray I (Easy — LeetCode #643)
# ─────────────────────────────────────────────
# Условие: найти максимальное среднее подмассива длиной k.


def find_max_average(nums: list[int], k: int) -> float:
    """
    O(n) time, O(1) space. Фиксированное окно.
    """
    window_sum = sum(nums[:k])
    best = window_sum
    for r in range(k, len(nums)):
        window_sum += nums[r] - nums[r - k]
        best = max(best, window_sum)
    return best / k


# ─────────────────────────────────────────────
# ТЕСТЫ
# ─────────────────────────────────────────────


def run_tests():
    print("═" * 50)
    print("ТЕСТЫ — Sliding Window паттерн")
    print("═" * 50)

    assert max_profit([7, 1, 5, 3, 6, 4]) == 5
    assert max_profit([7, 6, 4, 3, 1]) == 0
    assert max_profit([1]) == 0
    print("  ✓ max_profit")

    assert length_of_longest_substring("abcabcbb") == 3
    assert length_of_longest_substring("bbbbb") == 1
    assert length_of_longest_substring("pwwkew") == 3
    assert length_of_longest_substring("") == 0
    print("  ✓ length_of_longest_substring")

    assert check_inclusion("ab", "eidbaooo") is True
    assert check_inclusion("ab", "eidboaoo") is False
    print("  ✓ check_inclusion (permutation in string)")

    assert min_window("ADOBECODEBANC", "ABC") == "BANC"
    assert min_window("a", "a") == "a"
    assert min_window("a", "aa") == ""
    print("  ✓ min_window")

    assert find_max_average([1, 12, -5, -6, 50, 3], 4) == 12.75
    print("  ✓ find_max_average")

    print("\nВсе тесты прошли!")


def show_complexity_summary():
    print("\n═" * 50)
    print("РЕЗЮМЕ СЛОЖНОСТЕЙ")
    print("═" * 50)
    tasks = [
        (
            "Best Time to Buy Stock",
            "O(n) time, O(1) space",
            "l=покупка (min), r=продажа",
        ),
        ("Longest Substring No Repeat", "O(n) time, O(1) space", "seen dict + сдвиг l"),
        (
            "Permutation in String",
            "O(n) time, O(1) space",
            "фикс. окно, счётчик matches",
        ),
        ("Minimum Window Substring", "O(n+m) time, O(n+m) space", "have/need счётчик"),
        ("Max Average Subarray", "O(n) time, O(1) space", "скользящая сумма"),
    ]
    for name, complexity, trick in tasks:
        print(f"  {name}:")
        print(f"    {complexity}")
        print(f"    Трюк: {trick}")
        print()


if __name__ == "__main__":
    run_tests()
    show_complexity_summary()
