from __future__ import annotations

from core.content_language import classify_language_text


def test_russian_prose_passes() -> None:
    result = classify_language_text(
        """
        ## Почему это важно
        Эта заметка объясняет базовую идею простыми словами. Сначала мы читаем данные,
        затем проверяем структуру таблицы и только после этого строим выводы.
        """
    )

    assert result.classification == "ru_ok"


def test_english_prose_fails() -> None:
    result = classify_language_text(
        """
        ## Why it matters
        This lesson explains how to inspect data, prepare a clean table, and write a
        short analytical summary before building a model.
        """
    )

    assert result.classification == "too_much_english"


def test_code_blocks_do_not_cause_failure() -> None:
    result = classify_language_text(
        """
        ## Пример
        Ниже находится код. Он может содержать английские имена переменных, но объяснение
        вокруг него остаётся на русском языке.

        ```python
        import pandas as pd
        df = pd.read_csv("datasets/df_orders.csv")
        print(df.head())
        ```
        """
    )

    assert result.classification == "ru_ok"


def test_urls_do_not_cause_failure() -> None:
    result = classify_language_text(
        """
        ## Источники
        https://pandas.pydata.org/docs/user_guide/index.html

        ## Что сделать
        Прочитай короткое описание, открой таблицу и выпиши три наблюдения своими словами.
        """
    )

    assert result.classification == "ru_ok"


def test_mixed_ml_terms_are_allowed() -> None:
    result = classify_language_text(
        """
        ## Идея
        Для задачи baseline classifier важно явно разделить train/test split и проверить
        leakage. Термины embedding, RAG и model card могут оставаться английскими, если
        объяснение написано по-русски.
        """
    )

    assert result.classification in {"ru_ok", "mixed_ok"}
