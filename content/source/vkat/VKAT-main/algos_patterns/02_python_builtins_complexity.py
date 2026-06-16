"""
БЛОК 2 — Python Built-ins Complexity
======================================
Запусти: python 02_python_builtins_complexity.py
Это твоя шпаргалка + демонстрация через замеры времени.

ГЛАВНОЕ ПРАВИЛО: если интервьюер спросит "это не дорого?" —
ты должен мгновенно называть сложность встроенных операций.
"""

import time
import heapq
from collections import deque, defaultdict, Counter


# ─────────────────────────────────────────────
# ШПАРГАЛКА — выучи НАИЗУСТЬ
# ─────────────────────────────────────────────

CHEATSHEET = """
╔══════════════════════════════════════════════════════════════════════╗
║              PYTHON BUILT-INS COMPLEXITY CHEATSHEET                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIST (list)                                                         ║
║    append(x)          O(1)  amortized — добавить в конец            ║
║    pop()              O(1)  — удалить с конца                       ║
║    pop(i)             O(n)  — удалить по индексу (сдвиг элементов)  ║
║    insert(i, x)       O(n)  — вставка по индексу (сдвиг)           ║
║    x in list          O(n)  — линейный поиск!                       ║
║    list[i]            O(1)  — доступ по индексу                     ║
║    len(list)          O(1)  — хранится отдельно                     ║
║    sort() / sorted()  O(n log n)  — Timsort                         ║
║    list + list        O(n)  — создаёт новый список!                 ║
║    list * k           O(nk) — создаёт новый список!                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  DICT (dict)                                                         ║
║    d[key]             O(1)  average — hash lookup                   ║
║    d[key] = val       O(1)  average                                 ║
║    key in d           O(1)  average  ← ИСПОЛЬЗУЙ вместо list!       ║
║    del d[key]         O(1)  average                                 ║
║    d.get(key, def)    O(1)  average                                 ║
║    d.keys()           O(1)  — view, не копия                        ║
║    len(d)             O(1)                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  SET (set)                                                           ║
║    x in s             O(1)  average  ← ИСПОЛЬЗУЙ для быстрого поиска║
║    s.add(x)           O(1)  average                                 ║
║    s.remove(x)        O(1)  average                                 ║
║    s1 & s2            O(min(len(s1), len(s2)))  — intersection       ║
║    s1 | s2            O(len(s1) + len(s2))  — union                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  DEQUE (collections.deque)                                           ║
║    appendleft(x)      O(1)  ← vs list.insert(0) = O(n)!            ║
║    popleft()          O(1)  ← vs list.pop(0) = O(n)!               ║
║    append(x)          O(1)                                           ║
║    pop()              O(1)                                           ║
║    x in deque         O(n)  — линейный поиск                        ║
╠══════════════════════════════════════════════════════════════════════╣
║  HEAPQ (min-heap через list)                                         ║
║    heappush(h, x)     O(log n)                                       ║
║    heappop(h)         O(log n)  — всегда возвращает минимум         ║
║    heapify(list)      O(n)   — построить heap из списка             ║
║    h[0]               O(1)   — посмотреть минимум без удаления      ║
║  Для max-heap: пушь -x, pop даёт -минимум = максимум                ║
╠══════════════════════════════════════════════════════════════════════╣
║  СТРОКИ (str)                                                        ║
║    s[i]               O(1)                                           ║
║    s[i:j]             O(j-i)  — создаёт новую строку                ║
║    x in s             O(n)   — поиск подстроки                      ║
║    s + t              O(n+m) — создаёт новую строку!                ║
║    ''.join(list)      O(n)   ← ИСПОЛЬЗУЙ вместо += в цикле!        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

print(CHEATSHEET)


# ─────────────────────────────────────────────
# ДЕМОНСТРАЦИИ — видишь разницу в замерах
# ─────────────────────────────────────────────


def demo_list_vs_set_lookup():
    print("═" * 50)
    print("DEMO 1: list `in` vs set `in`")
    print("═" * 50)
    n = 500_000
    data_list = list(range(n))
    data_set = set(data_list)
    target = n - 1  # худший случай — последний элемент

    reps = 500
    t0 = time.perf_counter()
    for _ in range(reps):
        _ = target in data_list
    list_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    for _ in range(reps):
        _ = target in data_set
    set_ms = (time.perf_counter() - t0) * 1000

    print(f"  list `in` (O(n)):  {list_ms:.1f} ms")
    print(f"  set  `in` (O(1)):  {set_ms:.3f} ms")
    print(f"  Разница: {list_ms / max(set_ms, 0.001):.0f}x\n")


def demo_list_insert_vs_deque():
    print("═" * 50)
    print("DEMO 2: list.insert(0) vs deque.appendleft()")
    print("═" * 50)
    n = 50_000

    t0 = time.perf_counter()
    lst = []
    for i in range(n):
        lst.insert(0, i)
    list_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    dq = deque()
    for i in range(n):
        dq.appendleft(i)
    deque_ms = (time.perf_counter() - t0) * 1000

    print(f"  list.insert(0) (O(n) per op): {list_ms:.1f} ms total")
    print(f"  deque.appendleft (O(1)):       {deque_ms:.1f} ms total")
    print(f"  Разница: {list_ms / max(deque_ms, 0.001):.0f}x\n")


def demo_string_concat():
    print("═" * 50)
    print("DEMO 3: строка += vs ''.join()")
    print("═" * 50)
    n = 10_000

    t0 = time.perf_counter()
    s = ""
    for i in range(n):
        s += "x"
    concat_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    parts = []
    for i in range(n):
        parts.append("x")
    s = "".join(parts)
    join_ms = (time.perf_counter() - t0) * 1000

    print(f"  str +=  в цикле (O(n²)):  {concat_ms:.2f} ms")
    print(f"  ''.join(list) (O(n)):      {join_ms:.2f} ms")
    print(f"  Разница: {concat_ms / max(join_ms, 0.001):.1f}x")
    print("  Вывод: всегда строй список и join в конце!\n")


def demo_list_concat_trap():
    print("═" * 50)
    print("DEMO 4: result = result + [x] ЛОВУШКА (O(n²))")
    print("═" * 50)
    n = 20_000

    t0 = time.perf_counter()
    result = []
    for i in range(n):
        result = result + [i]  # создаёт новый список каждый раз!
    bad_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    result = []
    for i in range(n):
        result.append(i)  # O(1) amortized
    good_ms = (time.perf_counter() - t0) * 1000

    print(f"  result = result + [x] (O(n²)): {bad_ms:.1f} ms")
    print(f"  result.append(x) (O(n)):        {good_ms:.2f} ms")
    print(f"  Разница: {bad_ms / max(good_ms, 0.001):.0f}x")
    print("  ЭТУ ОШИБКУ часто делают в ML-коде!\n")


def demo_heapq():
    print("═" * 50)
    print("DEMO 5: heapq — Top K элементов")
    print("═" * 50)
    import random

    nums = [random.randint(1, 1000) for _ in range(100)]
    k = 5

    heap = []
    for n in nums:
        heapq.heappush(heap, n)

    top_k = []
    for _ in range(k):
        top_k.append(heapq.heappop(heap))

    print(f"  Nums sample: {nums[:10]}...")
    print(f"  Top-{k} smallest via heapq: {top_k}")
    print(f"  Time: O(n log n) для построения + O(k log n) для извлечения")

    # Или проще:
    top_k_fast = heapq.nsmallest(k, nums)
    print(f"  heapq.nsmallest({k}, nums) = {top_k_fast}")
    print(f"  heapq.nlargest({k}, nums)  = {heapq.nlargest(k, nums)}\n")


def demo_counter_defaultdict():
    print("═" * 50)
    print("DEMO 6: Counter и defaultdict — удобные dict-обёртки")
    print("═" * 50)
    words = ["apple", "banana", "apple", "cherry", "banana", "apple"]

    # Counter — подсчёт частоты O(n)
    cnt = Counter(words)
    print(f"  Counter: {cnt}")
    print(f"  Most common 2: {cnt.most_common(2)}")

    # defaultdict — избегаем KeyError
    dd = defaultdict(list)
    for i, w in enumerate(words):
        dd[w].append(i)
    print(f"  defaultdict(list): {dict(dd)}")
    print()


# ─────────────────────────────────────────────
# QUIZ — скажи вслух ответ, потом запусти
# ─────────────────────────────────────────────


def quiz():
    print("═" * 50)
    print("QUIZ — скажи ответ вслух, потом читай")
    print("═" * 50)
    questions = [
        ("d = {}; d['key'] = 1; 'key' in d", "O(1) average — dict lookup"),
        ("sorted(arr)", "O(n log n) time, O(n) space (новый список)"),
        ("arr.sort()", "O(n log n) time, O(1) space (in-place Timsort)"),
        ("deque.popleft()", "O(1) — это и есть смысл deque"),
        ("list.pop(0)", "O(n) — сдвигает все элементы! Используй deque"),
        ("heapq.heappush(h, x)", "O(log n)"),
        ("''.join(['a'] * n)", "O(n) — лучший способ собрать строку"),
        ("s = ''; s += 'x' (в цикле n раз)", "O(n²) — каждый += создаёт новую строку"),
        ("set(list_of_n)", "O(n) — построить set из списка"),
        ("list_a + list_b", "O(n+m) — создаёт НОВЫЙ список!"),
    ]
    for i, (code, answer) in enumerate(questions, 1):
        print(f"  Q{i}: {code}")
        print(f"  A:  {answer}")
        print()


if __name__ == "__main__":
    demo_list_vs_set_lookup()
    demo_list_insert_vs_deque()
    demo_string_concat()
    demo_list_concat_trap()
    demo_heapq()
    demo_counter_defaultdict()
    quiz()
