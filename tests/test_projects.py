import json
from pathlib import Path

from core.projects.loader import load_project_recipe, load_project_recipes, load_project_recipes_from_dirs
from core.projects.models import (
    calculate_readiness,
    checklist_progress,
    normalize_project_recipe,
    project_completion,
    project_progress,
)
from core.projects.progress import (
    completed_milestone_ids,
    is_project_complete,
    project_progress_from_record,
    set_checklist_item,
    set_milestone_completion,
    set_milestone_data,
    set_project_completion,
    set_project_completion_if_ready,
)
from core.tasks.runner import classify_task_result


def sample_project() -> dict:
    return {
        "id": "orders_eda",
        "title": "Orders EDA",
        "level": "beginner",
        "track": "Data Lab",
        "datasets": ["df_orders.csv"],
        "skills": ["pandas"],
        "estimated_time": "2 ч",
        "goal": "Build an EDA report.",
        "business_context": "Understand orders.",
        "prerequisites": ["Pandas"],
        "related_theory_paths": ["02_Data_Analysis/Pandas/02_Pandas_Course_Article.md"],
        "related_practice_ids": ["data_analysis_orders_eda"],
        "related_task_ids": ["analysis_3_pandas"],
        "related_dataset_names": ["df_orders.csv"],
        "related_portfolio_templates": [
            {
                "title": "Mini report",
                "what_to_write": "Explain the goal and findings.",
                "chart_or_table": "Daily revenue chart.",
                "readme_bullet": "Built an orders EDA report.",
            }
        ],
        "milestones": [
            {
                "id": "load",
                "title": "Load data",
                "type": "code",
                "description": "Load the CSV.",
                "dataset_hints": ["df_orders.csv"],
                "starter_code": "import pandas as pd",
                "checklist": ["Loaded data"],
                "portfolio_output": "Dataset overview",
            },
            {
                "id": "summary",
                "title": "Write summary",
                "type": "report",
                "description": "Write the result.",
                "reflection_prompt": "Write a concise report.",
                "checklist": ["Summary written"],
                "portfolio_output": "Mini report",
            },
            {
                "id": "optional_model_card",
                "title": "Optional model card",
                "type": "model_card",
                "description": "Write a model card if this becomes an ML project.",
                "test_code": "assert True",
                "required": False,
            },
        ],
        "deliverables": ["Report"],
        "portfolio_prompt": "Explain the analysis.",
    }


def test_normalize_project_recipe_keeps_required_fields() -> None:
    project = normalize_project_recipe(sample_project())

    assert project is not None
    assert project["id"] == "orders_eda"
    assert project["datasets"] == ["df_orders.csv"]
    assert project["related_dataset_names"] == ["df_orders.csv"]
    assert project["related_practice_ids"] == ["data_analysis_orders_eda"]
    assert project["related_task_ids"] == ["analysis_3_pandas"]
    assert project["related_portfolio_templates"][0]["title"] == "Mini report"
    assert len(project["milestones"]) == 3
    assert project["milestones"][0]["type"] == "code"
    assert project["milestones"][1]["type"] == "report"
    assert project["milestones"][1]["reflection_prompt"] == "Write a concise report."
    assert project["milestones"][2]["type"] == "model_card"
    assert project["milestones"][2]["test_code"] == "assert True"
    assert project["milestones"][2]["required"] is False


def test_normalize_project_recipe_rejects_invalid_milestones() -> None:
    raw = sample_project()
    raw["milestones"] = [{"id": "broken", "title": "Broken", "type": "unknown"}]

    assert normalize_project_recipe(raw) is None


def test_project_recipe_loading(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    path.write_text(json.dumps(sample_project()), encoding="utf-8")

    project = load_project_recipe(path)
    projects = load_project_recipes(tmp_path)

    assert project is not None
    assert project["title"] == "Orders EDA"
    assert len(projects) == 1
    assert projects[0]["source_path"] == str(path)


def test_project_recipe_loading_from_multiple_dirs(tmp_path: Path) -> None:
    first_dir = tmp_path / "data_lab"
    second_dir = tmp_path / "ml_lab"
    first_dir.mkdir()
    second_dir.mkdir()
    first = sample_project()
    second = sample_project() | {
        "id": "orders_conversion_baseline_classifier",
        "title": "Orders Conversion Baseline Classifier",
        "track": "Classic ML",
    }
    (first_dir / "orders.json").write_text(json.dumps(first), encoding="utf-8")
    (second_dir / "baseline.json").write_text(json.dumps(second), encoding="utf-8")

    projects = load_project_recipes_from_dirs((first_dir, second_dir))

    assert [project["id"] for project in projects] == [
        "orders_conversion_baseline_classifier",
        "orders_eda",
    ]


def test_ml_lab_baseline_recipe_loads() -> None:
    recipe = load_project_recipe("content/projects/ml_lab/orders_conversion_baseline_classifier.json")

    assert recipe is not None
    assert recipe["track"] == "Classic ML"
    assert recipe["datasets"] == ["df_events.csv", "df_orders.csv"]
    assert len(recipe["milestones"]) == 8
    assert {milestone["id"] for milestone in recipe["milestones"]} >= {
        "define_target",
        "train_test_split",
        "baseline_model",
        "evaluate_metrics",
        "model_card",
    }
    assert any("LogisticRegression" in milestone["starter_code"] for milestone in recipe["milestones"])


def test_project_progress_calculation() -> None:
    project = normalize_project_recipe(sample_project())
    assert project is not None

    stats = project_progress(project, {"load"})

    assert stats["total"] == 3
    assert stats["done"] == 1
    assert stats["todo"] == 2
    assert stats["ratio"] == 1 / 3
    assert stats["required_total"] == 2
    assert stats["required_done"] == 1
    assert stats["missing_required"] == ["summary"]


def test_milestone_completion_logic() -> None:
    project = normalize_project_recipe(sample_project())
    assert project is not None

    record = set_milestone_completion({}, "load", True, timestamp="2026-01-01T00:00:00Z")
    record = set_milestone_data(record, "load", {"solution_code": "print('ok')"}, timestamp="2026-01-01T00:00:01Z")

    assert completed_milestone_ids(record) == {"load"}
    assert project_progress_from_record(project, record)["done"] == 1
    assert record["milestones"]["load"]["solution_code"] == "print('ok')"

    record = set_milestone_completion(record, "load", False, timestamp="2026-01-01T00:01:00Z")

    assert completed_milestone_ids(record) == set()
    assert project_progress_from_record(project, record)["done"] == 0
    assert record["milestones"]["load"]["solution_code"] == "print('ok')"


def test_project_completion_flag_logic() -> None:
    project = normalize_project_recipe(sample_project())
    assert project is not None

    record = set_project_completion_if_ready(project, {}, True, timestamp="2026-01-01T00:00:00Z")
    assert is_project_complete(record) is False

    record = set_milestone_completion(record, "load", True, timestamp="2026-01-01T00:00:01Z")
    record = set_milestone_completion(record, "summary", True, timestamp="2026-01-01T00:00:02Z")
    record = set_project_completion_if_ready(project, record, True, timestamp="2026-01-01T00:00:03Z")
    assert is_project_complete(record) is True
    assert record["completed_at"] == "2026-01-01T00:00:03Z"

    record = set_project_completion(record, False, timestamp="2026-01-01T00:01:00Z")
    assert is_project_complete(record) is False
    assert record["completed_at"] == ""


def test_project_completion_uses_required_milestones_only() -> None:
    project = normalize_project_recipe(sample_project())
    assert project is not None

    assert project_completion(project, {"load", "summary"})["complete"] is True
    assert project_completion(project, {"load"})["complete"] is False


def test_checklist_progress_and_storage() -> None:
    checklist = ["title", "axis labels", "insight"]
    stats = checklist_progress(checklist, {"title", "insight"})

    assert stats == {"total": 3, "done": 2, "todo": 1, "ratio": 2 / 3, "complete": False}

    record = set_checklist_item({}, "viz", "title", True, timestamp="2026-01-01T00:00:00Z")
    record = set_checklist_item(record, "viz", "axis labels", True, timestamp="2026-01-01T00:00:01Z")
    record = set_checklist_item(record, "viz", "title", False, timestamp="2026-01-01T00:00:02Z")

    assert record["milestones"]["viz"]["checked_items"] == ["axis labels"]


def test_project_code_result_classification_reuses_task_classifier() -> None:
    assert classify_task_result({"ok": True, "outputs": []}) == "PASS"
    assert classify_task_result({"ok": False, "outputs": [{"type": "error", "ename": "AssertionError"}]}) == "FAIL"
    assert classify_task_result({"ok": False, "outputs": [{"type": "error", "ename": "NameError"}]}) == "ERROR"
    assert classify_task_result({"timed_out": True}) == "TIMEOUT"


def test_project_readiness_calculation() -> None:
    ready = calculate_readiness(
        [
            {"kind": "Theory", "label": "Pandas", "done": True},
            {"kind": "Practice", "label": "EDA", "done": True},
        ]
    )
    assert ready["status"] == "ready"
    assert ready["done"] == 2
    assert ready["missing"] == []

    almost = calculate_readiness(
        [
            {"kind": "Theory", "label": "Pandas", "done": True},
            {"kind": "Practice", "label": "EDA", "done": True},
            {"kind": "Tasks", "label": "Pandas tasks", "done": False},
        ]
    )
    assert almost["status"] == "almost ready"
    assert almost["missing"] == ["Pandas tasks"]

    not_ready = calculate_readiness(
        [
            {"kind": "Theory", "label": "Pandas", "done": False},
            {"kind": "Practice", "label": "EDA", "done": False},
        ]
    )
    assert not_ready["status"] == "not ready"
