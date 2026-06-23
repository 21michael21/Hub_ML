from __future__ import annotations

import hashlib
import os
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


_WHITESPACE_RE = re.compile(r"\s+")
EMBEDDINGS_FLAG = "HUBML_EMBEDDINGS"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


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
    backend: str = "tfidf"
    reason: str = ""
    model_name: str = ""
    embedding_model: Any = None


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
    return SearchIndex(items=searchable_items, vectorizer=vectorizer, matrix=matrix, backend="tfidf")


def embeddings_enabled() -> bool:
    return os.environ.get(EMBEDDINGS_FLAG, "").strip().casefold() in {"1", "true", "yes", "on"}


def default_embedding_cache_dir() -> Path:
    configured = os.environ.get("HUBML_SEARCH_CACHE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / "user_projects" / "search_cache"


def load_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> Any | None:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None

    try:
        return SentenceTransformer(model_name, device="cpu")
    except Exception:
        return None


def embedding_cache_key(model_name: str, items: list[SearchItem]) -> str:
    digest = hashlib.sha256()
    digest.update(model_name.encode("utf-8"))
    for item in items:
        digest.update(b"\0")
        digest.update(item.source.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
        digest.update(item.id.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
        digest.update(item_document(item).encode("utf-8", errors="ignore"))
    return digest.hexdigest()[:24]


def load_cached_embeddings(cache_path: Path) -> Any | None:
    try:
        with cache_path.open("rb") as handle:
            cached = pickle.load(handle)
    except (OSError, pickle.PickleError, EOFError):
        return None
    if not isinstance(cached, dict) or "matrix" not in cached:
        return None
    return cached["matrix"]


def save_cached_embeddings(cache_path: Path, matrix: Any) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("wb") as handle:
            pickle.dump({"matrix": matrix}, handle)
    except (OSError, pickle.PickleError):
        return


def build_embedding_index(
    items: Iterable[SearchItem],
    *,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path | None = None,
) -> SearchIndex | None:
    searchable_items = [item for item in items if item.id and item_document(item)]
    if not searchable_items:
        return SearchIndex(items=[], backend="embeddings", model_name=model_name)

    model = load_embedding_model(model_name)
    if model is None:
        return None

    documents = [item_document(item) for item in searchable_items]
    root = cache_dir or default_embedding_cache_dir()
    cache_path = root / f"{embedding_cache_key(model_name, searchable_items)}.pkl"
    matrix = load_cached_embeddings(cache_path)
    if matrix is None:
        try:
            matrix = model.encode(documents, normalize_embeddings=True, show_progress_bar=False)
        except Exception:
            return None
        save_cached_embeddings(cache_path, matrix)

    return SearchIndex(
        items=searchable_items,
        matrix=matrix,
        backend="embeddings",
        model_name=model_name,
        embedding_model=model,
    )


def build_search_index(
    items: Iterable[SearchItem],
    *,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path | None = None,
) -> SearchIndex:
    item_list = list(items)
    if embeddings_enabled():
        embedding_index = build_embedding_index(item_list, model_name=model_name, cache_dir=cache_dir)
        if embedding_index is not None:
            return embedding_index
        fallback = build_tfidf_index(item_list)
        fallback.reason = "embedding_backend_unavailable"
        return fallback
    return build_tfidf_index(item_list)


def search(
    index: SearchIndex,
    query: str,
    *,
    k: int = 5,
    exclude_ids: set[str] | None = None,
) -> list[SearchResult]:
    clean_query = normalize_search_text(query)
    if not clean_query or not index.items or index.matrix is None:
        return []

    if index.backend == "embeddings":
        if index.embedding_model is None:
            return []
        try:
            query_vector = index.embedding_model.encode(
                [clean_query],
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception:
            return []
    else:
        if index.vectorizer is None:
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
