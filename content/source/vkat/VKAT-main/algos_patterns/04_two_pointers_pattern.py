"""
БЛОК 4 — Паттерн: Two Pointers
================================
Запусти: python 04_two_pointers_pattern.py

СУТЬ ПАТТЕРНА:
  Два индекса (указателя) движутся по массиву/строке.
  Это позволяет обработать пары элементов за O(n) вместо O(n²).

ДВА ВАРИАНТА:
  1. Навстречу: l=0, r=n-1, двигаются к центру
     → когда массив отсортирован, ищем пару/проверяем симметрию
  2. В одну сторону: slow и fast
     → когда обрабатываем "подвижное окно" или in-place модификацию

КОГДА ПРИМЕНЯТЬ:
  - "Найди пару с суммой X" (отсортированный массив)
  - "Является ли строка палиндромом?"
  - "Удали дубликаты из отсортированного массива in-place"
  - "Контейнер с наибольшим количеством воды"
  - "Разворот массива/строки"
"""


# ─────────────────────────────────────────────
# ШАБЛОНЫ — заучи структуру
# ─────────────────────────────────────────────


def template_opposite_ends(arr):
    """Шаблон 1: указатели навстречу (отсортированный массив)."""
    l, r = 0, len(arr) - 1
    while l < r:
        current_sum = arr[l] + arr[r]
        if current_sum == target:
            return [l, r]  # нашли
        elif current_sum < target:
            l += 1  # нужна бо́льшая сумма
        else:
            r -= 1  # нужна меньшая сумма
    return []


def template_fast_slow(arr):
    """Шаблон 2: медленный и быстрый указатели."""
    slow = 0
    for fast in range(len(arr)):
        if arr[fast] != 0:  # условие для продвижения slow
            arr[slow] = arr[fast]
            slow += 1
    return slow  # slow — новая длина


# ─────────────────────────────────────────────
# ЗАДАЧА 1: Valid Palindrome (Easy — LeetCode #125)
# ─────────────────────────────────────────────
# Условие: строка с буквами и цифрами, остальное игнорировать.
# Является ли она палиндромом?
# Пример: "A man, a plan, a canal: Panama" → True


def is_palindrome(s: str) -> bool:
    """
    O(n) time, O(1) space.

    ОБЪЯСНЕНИЕ:
      "Два указателя — с обоих концов к центру.
       Пропускаем небуквенно-цифровые символы.
       Сравниваем символы без учёта регистра."
    """
    l, r = 0, len(s) - 1
    while l < r:
        while l < r and not s[l].isalnum():
            l += 1
        while l < r and not s[r].isalnum():
            r -= 1
        if s[l].lower() != s[r].lower():
            return False
        l += 1
        r -= 1
    return True


# ─────────────────────────────────────────────
# ЗАДАЧА 2: Two Sum II — Sorted Array (Medium — LeetCode #167)
# ─────────────────────────────────────────────
# Условие: ОТСОРТИРОВАННЫЙ массив (1-indexed). Найти два числа с суммой target.


def two_sum_sorted(numbers: list[int], target: int) -> list[int]:
    """
    O(n) time, O(1) space.
    Это классика two pointers — навстречу.

    ОБЪЯСНЕНИЕ:
      "Массив отсортирован → два указателя с краёв.
       Если сумма мала — двигаем левый вправо (увеличиваем).
       Если велика — двигаем правый влево (уменьшаем).
       Это работает потому что массив отсортирован!"
    """
    l, r = 0, len(numbers) - 1
    while l < r:
        s = numbers[l] + numbers[r]
        if s == target:
            return [l + 1, r + 1]  # 1-indexed
        elif s < target:
            l += 1
        else:
            r -= 1
    return []


# ─────────────────────────────────────────────
# ЗАДАЧА 3: Container With Most Water (Medium — LeetCode #11)
# ─────────────────────────────────────────────
# Условие: массив высот. Найди два индекса i,j для максимального объёма воды.
# Объём = (j - i) * min(height[i], height[j])
# Пример: [1,8,6,2,5,4,8,3,7] → 49


def max_area(height: list[int]) -> int:
    """
    O(n) time, O(1) space.

    ОБЪЯСНЕНИЕ:
      "Два указателя с краёв. Ширина максимальна.
       Двигаю тот указатель, который указывает на меньшую высоту —
       это единственный способ потенциально увеличить площадь.
       Двигать больший указатель бессмысленно: ширина уменьшится,
       а высота ограничена меньшим."
    """
    l, r = 0, len(height) - 1
    best = 0
    while l < r:
        water = (r - l) * min(height[l], height[r])
        best = max(best, water)
        if height[l] < height[r]:
            l += 1
        else:
            r -= 1
    return best


# ─────────────────────────────────────────────
# ЗАДАЧА 4: Remove Duplicates from Sorted Array (Easy — LeetCode #26)
# ─────────────────────────────────────────────
# Условие: ОТСОРТИРОВАННЫЙ массив. Удалить дубликаты in-place.
# Вернуть длину уникальной части. Порядок сохранить.
# Пример: [1,1,2] → 2, массив [1,2,...]


def remove_duplicates(nums: list[int]) -> int:
    """
    O(n) time, O(1) space — in-place, fast/slow шаблон.

    ОБЪЯСНЕНИЕ:
      "slow указывает на место для следующего уникального элемента.
       fast проходит по всему массиву.
       Если fast нашёл новый элемент — копируем на место slow, slow++."
    """
    if not nums:
        return 0
    slow = 1
    for fast in range(1, len(nums)):
        if nums[fast] != nums[fast - 1]:
            nums[slow] = nums[fast]
            slow += 1
    return slow


# ─────────────────────────────────────────────
# ЗАДАЧА 5: 3Sum (Medium — LeetCode #15)
# ─────────────────────────────────────────────
# Условие: найти все тройки с суммой 0 (без дубликатов в результате).
# Пример: [-1,0,1,2,-1,-4] → [[-1,-1,2],[-1,0,1]]


def three_sum(nums: list[int]) -> list[list[int]]:
    """
    O(n²) time, O(n) space (для вывода).

    ОБЪЯСНЕНИЕ:
      "Сортирую массив. Для каждого nums[i] — задача two sum
       в остатке массива с target = -nums[i].
       Используем two pointers для этого two sum.
       Пропускаем дубликаты чтобы не повторять тройки."
    """
    nums.sort()
    result = []

    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i - 1]:  # пропускаем дубликат i
            continue

        l, r = i + 1, len(nums) - 1
        while l < r:
            total = nums[i] + nums[l] + nums[r]
            if total == 0:
                result.append([nums[i], nums[l], nums[r]])
                while l < r and nums[l] == nums[l + 1]:  # пропуск дублей l
                    l += 1
                while l < r and nums[r] == nums[r - 1]:  # пропуск дублей r
                    r -= 1
                l += 1
                r -= 1
            elif total < 0:
                l += 1
            else:
                r -= 1

    return result


# ─────────────────────────────────────────────
# ЗАДАЧА 6: Move Zeroes (Easy — LeetCode #283)
# ─────────────────────────────────────────────
# Условие: переместить все нули в конец массива in-place, порядок сохранить.
# Пример: [0,1,0,3,12] → [1,3,12,0,0]


def move_zeroes(nums: list[int]) -> None:
    """
    O(n) time, O(1) space — fast/slow шаблон.
    """
    slow = 0
    for fast in range(len(nums)):
        if nums[fast] != 0:
            nums[slow] = nums[fast]
            slow += 1
    while slow < len(nums):
        nums[slow] = 0
        slow += 1


# ─────────────────────────────────────────────
# ТЕСТЫ
# ─────────────────────────────────────────────


def run_tests():
    print("═" * 50)
    print("ТЕСТЫ — Two Pointers паттерн")
    print("═" * 50)

    assert is_palindrome("A man, a plan, a canal: Panama") is True
    assert is_palindrome("race a car") is False
    assert is_palindrome(" ") is True
    print("  ✓ is_palindrome")

    assert two_sum_sorted([2, 7, 11, 15], 9) == [1, 2]
    assert two_sum_sorted([2, 3, 4], 6) == [1, 3]
    print("  ✓ two_sum_sorted")

    assert max_area([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49
    assert max_area([1, 1]) == 1
    print("  ✓ max_area (Container With Most Water)")

    nums = [1, 1, 2]
    k = remove_duplicates(nums)
    assert k == 2 and nums[:k] == [1, 2]
    nums = [0, 0, 1, 1, 1, 2, 2, 3, 3, 4]
    k = remove_duplicates(nums)
    assert k == 5 and nums[:k] == [0, 1, 2, 3, 4]
    print("  ✓ remove_duplicates")

    result = three_sum([-1, 0, 1, 2, -1, -4])
    assert sorted(result) == sorted([[-1, -1, 2], [-1, 0, 1]])
    assert three_sum([0, 0, 0]) == [[0, 0, 0]]
    assert three_sum([1]) == []
    print("  ✓ three_sum")

    nums = [0, 1, 0, 3, 12]
    move_zeroes(nums)
    assert nums == [1, 3, 12, 0, 0]
    print("  ✓ move_zeroes")

    print("\nВсе тесты прошли!")


def show_complexity_summary():
    print("\n═" * 50)
    print("РЕЗЮМЕ СЛОЖНОСТЕЙ")
    print("═" * 50)
    tasks = [
        (
            "Valid Palindrome",
            "O(n) time, O(1) space",
            "два указателя навстречу, skip non-alnum",
        ),
        (
            "Two Sum II (sorted)",
            "O(n) time, O(1) space",
            "навстречу, сдвигаем по условию суммы",
        ),
        (
            "Container With Most Water",
            "O(n) time, O(1) space",
            "двигаем меньшую высоту",
        ),
        (
            "Remove Duplicates",
            "O(n) time, O(1) space",
            "fast/slow: slow = место для уник. элемента",
        ),
        ("3Sum", "O(n²) time, O(n) space", "сортировка + two pointers для каждого i"),
        (
            "Move Zeroes",
            "O(n) time, O(1) space",
            "fast/slow: slow = место для non-zero",
        ),
    ]
    for name, complexity, trick in tasks:
        print(f"  {name}:")
        print(f"    {complexity}")
        print(f"    Трюк: {trick}")
        print()


if __name__ == "__main__":
    run_tests()
    show_complexity_summary()
