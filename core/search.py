from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class SearchItem:
    source: str
    id: str
    title: str
    body: str = ""
    path: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    source: str
    id: str
    title: str
    score: float
    path: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchIndex:
    items: list[SearchItem]
    vectorizer: TfidfVectorizer | None = None
    matrix: Any = None


def normalize_search_text(value: object) -> str:
    text = str(value or "").replace("\x00", " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def item_document(item: SearchItem) -> str:
    return normalize_search_text(f"{item.title}\n{item.body}")


def build_tfidf_index(items: Iterable[SearchItem]) -> SearchIndex:
    searchable_items = [item for item in items if item.id and item_document(item)]
    if not searchable_items:
        return SearchIndex(items=[])

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=1,
    )
    documents = [item_document(item) for item in searchable_items]
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return SearchIndex(items=[])
    return SearchIndex(items=searchable_items, vectorizer=vectorizer, matrix=matrix)


def search(
    index: SearchIndex,
    query: str,
    *,
    k: int = 5,
    exclude_ids: set[str] | None = None,
) -> list[SearchResult]:
    clean_query = normalize_search_text(query)
    if not clean_query or not index.items or index.vectorizer is None or index.matrix is None:
        return []

    query_vector = index.vectorizer.transform([clean_query])
    scores = cosine_similarity(query_vector, index.matrix).ravel()
    excluded = exclude_ids or set()
    ranked_indexes = sorted(range(len(scores)), key=lambda idx: float(scores[idx]), reverse=True)

    results: list[SearchResult] = []
    for item_index in ranked_indexes:
        item = index.items[item_index]
        score = float(scores[item_index])
        if score <= 0 or item.id in excluded:
            continue
        results.append(
            SearchResult(
                source=item.source,
                id=item.id,
                title=item.title,
                score=score,
                path=item.path,
                payload=dict(item.payload),
            )
        )
        if len(results) >= k:
            break
    return results
