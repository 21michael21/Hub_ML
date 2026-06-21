from __future__ import annotations

from core.internal_links import (
    InternalTarget,
    build_internal_indexes,
    validate_internal_target,
)


def sample_indexes():
    return build_internal_indexes(
        notes=[{"relative_path": "00_Atlas/00_Knowledge_Map.md"}],
        tasks=[{"id": "python_basics_records"}],
        projects=[{"id": "orders_eda", "milestones": [{"id": "load_data"}]}],
        practice_cards=[{"id": "portfolio_readme_outline"}],
        datasets=[{"name": "df_orders.csv"}],
        reports=["content/reports/theory_audit.json"],
    )


def test_theory_note_target_validates_by_relative_path_not_display_label() -> None:
    indexes = sample_indexes()

    valid = validate_internal_target(
        InternalTarget(
            kind="theory_note",
            label="00 Atlas / 00_Knowledge_Map.md",
            path="00_Atlas/00_Knowledge_Map.md",
        ),
        indexes,
    )
    invalid = validate_internal_target(
        InternalTarget(
            kind="theory_note",
            label="00 Atlas / 00_Knowledge_Map.md",
            path="00 Atlas / 00_Knowledge_Map.md",
        ),
        indexes,
    )

    assert valid.exists is True
    assert invalid.exists is False
    assert "theory note not found" in invalid.reason


def test_task_target_validates_against_mentor_task_ids() -> None:
    result = validate_internal_target(
        InternalTarget(kind="task", label="Python basics", target_id="python_basics_records"),
        sample_indexes(),
    )

    assert result.exists is True
    assert result.resolved == "python_basics_records"


def test_project_milestone_target_validates_against_project_recipes() -> None:
    result = validate_internal_target(
        InternalTarget(
            kind="milestone",
            label="Load data",
            project_id="orders_eda",
            milestone_id="load_data",
        ),
        sample_indexes(),
    )

    assert result.exists is True
    assert result.resolved == "orders_eda::load_data"


def test_dataset_target_validates_against_dataset_registry() -> None:
    result = validate_internal_target(
        InternalTarget(kind="dataset", label="Orders", target_id="df_orders.csv"),
        sample_indexes(),
    )

    assert result.exists is True


def test_invalid_target_returns_clear_result_not_crash() -> None:
    result = validate_internal_target(
        InternalTarget(kind="dataset", label="Missing", target_id="missing.csv"),
        sample_indexes(),
    )

    assert result.exists is False
    assert result.reason == "dataset not found: missing.csv"


def test_unknown_target_kind_returns_clear_result_not_crash() -> None:
    result = validate_internal_target(
        InternalTarget(kind="external_url", label="Docs", target_id="https://example.test"),
        sample_indexes(),
    )

    assert result.exists is False
    assert result.reason == "unknown target kind: external_url"
