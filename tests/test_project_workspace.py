import json
from pathlib import Path

from core.projects.workspace import (
    create_project_workspace,
    project_workspace_files,
    project_workspace_path,
    relative_dataset_reference,
    render_portfolio_markdown_template,
    render_workspace_readme,
    safe_project_slug,
)


def sample_project() -> dict:
    return {
        "id": "orders_conversion_baseline_classifier",
        "title": "Orders Conversion Baseline Classifier",
        "goal": "Build a baseline classifier.",
        "business_context": "Learn honest baseline modeling.",
        "datasets": ["df_events.csv", "df_orders.csv"],
        "related_dataset_names": ["df_events.csv", "df_orders.csv"],
        "skills": ["pandas", "classification"],
        "source_path": "content/projects/ml_lab/orders_conversion_baseline_classifier.json",
        "milestones": [
            {
                "id": "define_target",
                "title": "Define target",
                "type": "reading",
                "description": "Define the target.",
                "checklist": ["Target is binary"],
                "portfolio_output": "Target paragraph",
            },
            {
                "id": "model_card",
                "title": "Write model card",
                "type": "model_card",
                "description": "Write the card.",
                "required": True,
            },
        ],
        "deliverables": ["Notebook", "Model card"],
        "related_portfolio_templates": [
            {
                "readme_bullet": "Built a conversion baseline classifier with pandas and scikit-learn."
            }
        ],
    }


def test_safe_project_slug() -> None:
    assert safe_project_slug("Orders Conversion Baseline Classifier!") == "orders-conversion-baseline-classifier"
    assert safe_project_slug("   ") == "project"
    assert len(safe_project_slug("x" * 200)) == 80


def test_project_workspace_path_generation(tmp_path: Path) -> None:
    path = project_workspace_path(sample_project(), tmp_path)

    assert path == tmp_path / "orders-conversion-baseline-classifier"


def test_relative_dataset_reference() -> None:
    ref = relative_dataset_reference(
        "/repo",
        "/repo/user_projects/orders_conversion_baseline_classifier",
        "df_orders.csv",
    )

    assert ref == "../../datasets/df_orders.csv"


def test_markdown_templates_include_project_context() -> None:
    project = sample_project()
    readme = render_workspace_readme(project, ["../../datasets/df_events.csv", "../../datasets/df_orders.csv"])
    portfolio = render_portfolio_markdown_template(project)

    assert "# Orders Conversion Baseline Classifier" in readme
    assert "Build a baseline classifier." in readme
    assert "../../datasets/df_orders.csv" in readme
    assert "Do not copy raw datasets" in readme
    assert "## Resume Bullet Draft" in portfolio
    assert "Built a conversion baseline classifier" in portfolio


def test_project_workspace_files_do_not_include_raw_datasets(tmp_path: Path) -> None:
    workspace = tmp_path / "user_projects" / "orders_conversion_baseline_classifier"
    files = project_workspace_files(sample_project(), workspace, tmp_path, "2026-01-01T00:00:00Z")

    assert "README.md" in files
    assert "project.json" in files
    assert "datasets/df_orders.csv" not in files
    manifest = json.loads(files["project.json"])
    assert manifest["project_id"] == "orders_conversion_baseline_classifier"
    assert manifest["milestone_ids"] == ["define_target", "model_card"]


def test_create_project_workspace_no_overwrite(tmp_path: Path) -> None:
    root = tmp_path / "user_projects"
    project_root = tmp_path
    result = create_project_workspace(
        sample_project(),
        root,
        project_root,
        created_at="2026-01-01T00:00:00Z",
    )

    assert result["created"] is True
    workspace = Path(result["path"])
    readme = workspace / "README.md"
    assert readme.exists()
    readme.write_text("custom user notes", encoding="utf-8")

    second = create_project_workspace(
        sample_project(),
        root,
        project_root,
        created_at="2026-01-01T00:00:01Z",
    )
    assert second == {"created": False, "exists": True, "path": str(workspace), "written": []}
    assert readme.read_text(encoding="utf-8") == "custom user notes"

    third = create_project_workspace(
        sample_project(),
        root,
        project_root,
        overwrite=True,
        created_at="2026-01-01T00:00:02Z",
    )
    assert third["created"] is True
    assert readme.read_text(encoding="utf-8").startswith("# Orders Conversion Baseline Classifier")
