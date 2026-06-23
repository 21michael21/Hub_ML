from __future__ import annotations

from core.search import SearchItem, build_search_index, build_tfidf_index, search


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


def test_default_search_backend_is_tfidf(monkeypatch) -> None:
    monkeypatch.delenv("HUBML_EMBEDDINGS", raising=False)

    index = build_search_index(
        [SearchItem(source="note", id="python", title="Python", body="lists dicts functions")]
    )

    assert index.backend == "tfidf"
    assert search(index, "lists")[0].id == "python"


def test_embedding_backend_falls_back_when_optional_package_missing(monkeypatch) -> None:
    monkeypatch.setenv("HUBML_EMBEDDINGS", "1")
    monkeypatch.setattr("core.search.load_embedding_model", lambda *_args, **_kwargs: None)

    index = build_search_index(
        [SearchItem(source="note", id="python", title="Python", body="lists dicts functions")]
    )

    assert index.backend == "tfidf"
    assert index.reason == "embedding_backend_unavailable"
    assert search(index, "functions")[0].id == "python"
