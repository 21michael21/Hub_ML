from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ALLOWED_LATIN_TERMS = {
    "ab",
    "ai",
    "api",
    "baseline",
    "csv",
    "dataframe",
    "dataset",
    "docker",
    "embedding",
    "embeddings",
    "fastapi",
    "f1",
    "genai",
    "git",
    "github",
    "groupby",
    "json",
    "jupyter",
    "kaggle",
    "leakage",
    "llm",
    "matplotlib",
    "merge",
    "ml",
    "mlops",
    "model",
    "model card",
    "nlp",
    "notebook",
    "numpy",
    "openai",
    "pandas",
    "pytest",
    "rag",
    "read_csv",
    "readme",
    "roc_auc",
    "scikit",
    "sklearn",
    "sql",
    "streamlit",
    "test",
    "train",
    "train/test split",
}

FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.DOTALL)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
SOURCE_HEADING_RE = re.compile(
    r"^(#{1,6})\s*(sources?|references?|источники|источники\s*/\s*references)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class LanguageAuditResult:
    path: str
    classification: str
    cyrillic_letters: int
    latin_letters: int
    russian_ratio: float
    reason: str


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub("", text, count=1)


def strip_source_sections(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    skipping = False
    source_level = 0
    for line in lines:
        match = SOURCE_HEADING_RE.match(line)
        if match:
            skipping = True
            source_level = len(match.group(1))
            continue
        if skipping:
            heading = re.match(r"^(#{1,6})\s+", line)
            if heading and len(heading.group(1)) <= source_level:
                skipping = False
            else:
                continue
        if not skipping:
            output.append(line)
    return "\n".join(output)


def normalize_prose(text: str) -> str:
    text = strip_frontmatter(text)
    text = FENCED_CODE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = strip_source_sections(text)
    text = HTML_TAG_RE.sub(" ", text)
    for term in sorted(ALLOWED_LATIN_TERMS, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        text = pattern.sub(" ", text)
    return text


def classify_language_text(text: str, path: str = "") -> LanguageAuditResult:
    prose = normalize_prose(text)
    cyrillic = len(CYRILLIC_RE.findall(prose))
    latin = len(LATIN_RE.findall(prose))
    total = cyrillic + latin
    ratio = cyrillic / total if total else 1.0

    if total < 40:
        classification = "code_or_source_only"
        reason = "too little prose after ignoring code, urls, and sources"
    elif cyrillic == 0 and latin >= 40:
        classification = "too_much_english"
        reason = "english prose without russian explanation"
    elif ratio >= 0.55:
        classification = "ru_ok"
        reason = "russian prose dominates"
    elif ratio >= 0.35 and latin <= max(160, cyrillic * 1.7):
        classification = "mixed_ok"
        reason = "mixed prose with enough russian explanation"
    else:
        classification = "too_much_english"
        reason = "latin prose dominates russian explanation"

    return LanguageAuditResult(
        path=Path(path).as_posix() if path else "",
        classification=classification,
        cyrillic_letters=cyrillic,
        latin_letters=latin,
        russian_ratio=round(ratio, 3),
        reason=reason,
    )
