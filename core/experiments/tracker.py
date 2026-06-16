from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_EXPERIMENT_STATUSES = {"draft", "completed", "failed"}
CLASSIFICATION_METRICS = ("accuracy", "precision", "recall", "f1", "roc_auc")
REGRESSION_METRICS = ("mae", "rmse", "r2")
SUPPORTED_METRICS = CLASSIFICATION_METRICS + REGRESSION_METRICS


def as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in re.split(r"[,\n]", value) if item.strip()]
    return []


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def numeric_metrics(value: Any) -> dict[str, float]:
    raw = as_dict(value)
    metrics: dict[str, float] = {}
    for key, metric_value in raw.items():
        name = str(key).strip()
        if not name:
            continue
        try:
            metrics[name] = float(metric_value)
        except (TypeError, ValueError):
            continue
    return metrics


def normalize_experiment_record(raw: dict[str, Any]) -> dict[str, Any]:
    timestamp = str(raw.get("timestamp") or datetime.now(timezone.utc).isoformat()).strip()
    project_id = str(raw.get("project_id") or "").strip()
    experiment_id = str(raw.get("id") or "").strip() or f"exp-{uuid.uuid4().hex[:12]}"
    status = str(raw.get("status") or "draft").strip().casefold()
    if status not in VALID_EXPERIMENT_STATUSES:
        status = "draft"

    return {
        "id": experiment_id,
        "timestamp": timestamp,
        "project_id": project_id,
        "dataset_names": as_string_list(raw.get("dataset_names")),
        "target_column": str(raw.get("target_column") or "").strip(),
        "feature_columns": as_string_list(raw.get("feature_columns")),
        "model_name": str(raw.get("model_name") or "").strip(),
        "parameters": as_dict(raw.get("parameters")),
        "metrics": numeric_metrics(raw.get("metrics")),
        "notes": str(raw.get("notes") or "").strip(),
        "code_snippet": str(raw.get("code_snippet") or "").strip(),
        "artifact_paths": as_string_list(raw.get("artifact_paths")),
        "status": status,
    }


def save_experiment_record(record: dict[str, Any], experiments_path: str | Path) -> dict[str, Any]:
    normalized = normalize_experiment_record(record)
    path = Path(experiments_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(normalized, ensure_ascii=False, sort_keys=True) + "\n")
    return normalized


def load_experiment_records(experiments_path: str | Path) -> list[dict[str, Any]]:
    path = Path(experiments_path)
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            records.append(normalize_experiment_record(raw))
    return records


def summarize_experiments(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    by_status = {status: 0 for status in sorted(VALID_EXPERIMENT_STATUSES)}
    metric_names: set[str] = set()
    for record in records:
        status = str(record.get("status") or "draft")
        by_status[status] = by_status.get(status, 0) + 1
        metrics = record.get("metrics")
        if isinstance(metrics, dict):
            metric_names.update(str(name) for name in metrics)
    return {
        "total": total,
        "by_status": by_status,
        "metric_names": sorted(metric_names),
    }


def compare_experiments(
    records: list[dict[str, Any]],
    metric_name: str,
    *,
    descending: bool = True,
) -> list[dict[str, Any]]:
    metric = str(metric_name or "").strip()
    rows: list[dict[str, Any]] = []
    for record in records:
        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        value = metrics.get(metric)
        rows.append(
            {
                "id": record.get("id", ""),
                "timestamp": record.get("timestamp", ""),
                "status": record.get("status", ""),
                "model_name": record.get("model_name", ""),
                "metric": metric,
                "value": value if isinstance(value, (int, float)) else None,
                "notes": record.get("notes", ""),
            }
        )
    rows.sort(
        key=lambda item: (
            item["value"] is None,
            -(float(item["value"]) if item["value"] is not None else 0.0) if descending else (float(item["value"]) if item["value"] is not None else 0.0),
            str(item["timestamp"]),
        )
    )
    return rows


def experiment_records_path(project_workspace: str | Path) -> Path:
    return Path(project_workspace) / "experiments" / "experiments.jsonl"
