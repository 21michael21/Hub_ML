from __future__ import annotations

from core.search import SearchItem, build_tfidf_index, search


def test_semantic_search_ranks_expected_item_first() -> None:
    index = build_tfidf_index(
        [
            SearchItem(
                source="note",
                id="python-basics",
                title="Python Basics",
                body="Переменные, списки, словари и функции для обработки записей.",
            ),
            SearchItem(
                source="practice",
                id="sql-window-practice",
                title="Window Functions Practice",
                body="SQL window function with partition by, ranking and running total.",
            ),
            SearchItem(
                source="task",
                id="pandas-groupby-task",
                title="Pandas GroupBy",
                body="Сгруппируй события через groupby и посчитай агрегаты.",
            ),
        ]
    )

    results = search(index, "partition ranking window", k=2)

    assert [result.id for result in results] == ["sql-window-practice"]
    assert results[0].source == "practice"
    assert results[0].score > 0


def test_semantic_search_handles_empty_index_and_query() -> None:
    empty_index = build_tfidf_index([])

    assert search(empty_index, "python") == []

    index = build_tfidf_index(
        [SearchItem(source="note", id="python", title="Python", body="lists dicts functions")]
    )

    assert search(index, "") == []


def test_semantic_search_can_exclude_current_item() -> None:
    index = build_tfidf_index(
        [
            SearchItem(source="note", id="current", title="Pandas", body="pandas dataframe filtering"),
            SearchItem(source="task", id="task", title="Pandas task", body="pandas dataframe filtering task"),
        ]
    )

    results = search(index, "pandas dataframe", k=3, exclude_ids={"current"})

    assert [result.id for result in results] == ["task"]
