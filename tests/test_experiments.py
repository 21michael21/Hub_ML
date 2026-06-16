from pathlib import Path

from core.experiments.tracker import (
    compare_experiments,
    experiment_records_path,
    load_experiment_records,
    normalize_experiment_record,
    save_experiment_record,
    summarize_experiments,
)


def test_normalize_experiment_record() -> None:
    record = normalize_experiment_record(
        {
            "id": "",
            "timestamp": "2026-01-01T00:00:00Z",
            "project_id": "orders_conversion_baseline_classifier",
            "dataset_names": "df_events.csv, df_orders.csv",
            "target_column": "converted",
            "feature_columns": "events_total\ncart_shown",
            "model_name": "LogisticRegression",
            "parameters": '{"class_weight": "balanced", "max_iter": 1000}',
            "metrics": {"accuracy": "0.84", "f1": 0.8, "bad": "n/a"},
            "notes": "baseline",
            "code_snippet": "model.fit(X_train, y_train)",
            "artifact_paths": "artifacts/tables/metrics.csv",
            "status": "COMPLETED",
        }
    )

    assert record["id"].startswith("exp-")
    assert record["dataset_names"] == ["df_events.csv", "df_orders.csv"]
    assert record["feature_columns"] == ["events_total", "cart_shown"]
    assert record["parameters"] == {"class_weight": "balanced", "max_iter": 1000}
    assert record["metrics"] == {"accuracy": 0.84, "f1": 0.8}
    assert record["status"] == "completed"


def test_experiment_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "experiments.jsonl"
    saved = save_experiment_record(
        {
            "id": "exp-1",
            "timestamp": "2026-01-01T00:00:00Z",
            "project_id": "p1",
            "metrics": {"accuracy": 0.7},
            "status": "completed",
        },
        path,
    )

    loaded = load_experiment_records(path)

    assert saved["id"] == "exp-1"
    assert loaded == [saved]


def test_compare_experiments_sorting_and_missing_metrics() -> None:
    records = [
        normalize_experiment_record({"id": "a", "metrics": {"f1": 0.4}, "model_name": "A"}),
        normalize_experiment_record({"id": "b", "metrics": {"f1": 0.8}, "model_name": "B"}),
        normalize_experiment_record({"id": "c", "metrics": {"accuracy": 0.9}, "model_name": "C"}),
    ]

    rows = compare_experiments(records, "f1")

    assert [row["id"] for row in rows] == ["b", "a", "c"]
    assert rows[-1]["value"] is None


def test_summarize_experiments() -> None:
    records = [
        normalize_experiment_record({"status": "completed", "metrics": {"accuracy": 0.9}}),
        normalize_experiment_record({"status": "failed", "metrics": {"f1": 0.5}}),
    ]

    summary = summarize_experiments(records)

    assert summary["total"] == 2
    assert summary["by_status"]["completed"] == 1
    assert summary["by_status"]["failed"] == 1
    assert summary["metric_names"] == ["accuracy", "f1"]


def test_experiment_records_path() -> None:
    assert experiment_records_path("/repo/user_projects/p1") == Path("/repo/user_projects/p1/experiments/experiments.jsonl")
