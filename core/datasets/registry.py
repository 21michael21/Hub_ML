from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def count_csv_rows(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            line_count = sum(1 for _ in handle)
    except OSError:
        return None
    return max(line_count - 1, 0)


@st.cache_data(show_spinner=False)
def scan_datasets(datasets_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(datasets_dir)
    if not root.exists() or not root.is_dir():
        return []

    datasets: list[dict[str, Any]] = []
    for csv_path in sorted(root.glob("*.csv"), key=lambda path: path.name.casefold()):
        if csv_path.name.startswith("."):
            continue

        record: dict[str, Any] = {
            "name": csv_path.name,
            "path": str(csv_path),
            "size_bytes": csv_path.stat().st_size,
            "size": format_bytes(csv_path.stat().st_size),
            "rows": None,
            "columns": None,
            "error": None,
        }
        try:
            header = pd.read_csv(csv_path, nrows=0)
            record["columns"] = len(header.columns)
            record["rows"] = count_csv_rows(csv_path)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
            record["error"] = str(exc)

        datasets.append(record)

    return datasets


@st.cache_data(show_spinner=False)
def read_dataset_preview(path: str, nrows: int = 50) -> dict[str, Any]:
    try:
        preview = pd.read_csv(path, nrows=nrows)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
        return {"error": str(exc), "preview": None, "dtypes": None, "describe": None}

    numeric = preview.select_dtypes(include="number")
    describe = numeric.describe().transpose() if not numeric.empty else None
    return {
        "error": None,
        "preview": preview,
        "dtypes": preview.dtypes.astype(str).reset_index().rename(
            columns={"index": "column", 0: "dtype"}
        ),
        "describe": describe,
    }


def find_dataset_record(name: str, datasets: list[dict[str, Any]]) -> dict[str, Any] | None:
    wanted = str(name or "").strip().casefold()
    if not wanted:
        return None
    return next((dataset for dataset in datasets if dataset["name"].casefold() == wanted), None)
