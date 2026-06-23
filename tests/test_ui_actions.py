from __future__ import annotations

from core.internal_links import build_internal_indexes
from core.ui_actions import UIAction, UIActionIndexes, validate_ui_action, validate_ui_actions


def sample_action_indexes() -> UIActionIndexes:
    return UIActionIndexes(
        internal=build_internal_indexes(
            notes=[{"relative_path": "00_Atlas/00_Knowledge_Map.md"}],
            tasks=[{"id": "python_basics_records"}],
            projects=[{"id": "orders_eda", "milestones": [{"id": "load_data"}]}],
            practice_cards=[{"id": "pandas_basics"}],
            datasets=[{"name": "df_orders.csv"}],
            reports=["content/reports/theory_audit.json"],
        ),
        known_state_keys={"active_tab", "active_note_path", "selected_mentor_task"},
        tabs={"Home", "Theory", "🎯 Tasks"},
    )


def test_valid_navigate_action_passes() -> None:
    action = UIAction(
        action_id="home.open_theory",
        label="Открыть теорию",
        action_type="navigate",
        target_kind="theory_note",
        path="00_Atlas/00_Knowledge_Map.md",
        required_state_keys=("active_tab", "active_note_path"),
    )

    result = validate_ui_action(action, sample_action_indexes())

    assert result.ok is True
    assert result.severity == "pass"


def test_missing_target_fails_clearly() -> None:
    action = UIAction(
        action_id="home.open_missing_task",
        label="Открыть задачу",
        action_type="navigate",
        target_kind="task",
        target_id="missing_task",
    )

    result = validate_ui_action(action, sample_action_indexes())

    assert result.ok is False
    assert result.target_exists is False
    assert result.reason == "task not found: missing_task"


def test_missing_state_key_fails_clearly() -> None:
    action = UIAction(
        action_id="task.open",
        label="Открыть",
        action_type="set_state",
        target_kind="task",
        target_id="python_basics_records",
        required_state_keys=("unknown_state_key",),
    )

    result = validate_ui_action(action, sample_action_indexes())

    assert result.ok is False
    assert result.state_keys_ok is False
    assert "unknown_state_key" in result.reason


def test_unsafe_action_is_reported_but_not_failed() -> None:
    action = UIAction(
        action_id="task.run_check",
        label="▶ Проверить",
        action_type="run_check",
        target_kind="task",
        target_id="python_basics_records",
        required_state_keys=("selected_mentor_task",),
        safe_to_e2e_click=False,
    )

    result = validate_ui_action(action, sample_action_indexes())

    assert result.ok is True
    assert result.severity == "warning"
    assert "unsafe to e2e click" in result.reason


def test_duplicate_action_ids_fail() -> None:
    actions = [
        UIAction(
            action_id="home.open_theory",
            label="Открыть теорию",
            action_type="navigate",
            target_kind="tab",
            target_id="Theory",
        ),
        UIAction(
            action_id="home.open_theory",
            label="Открыть теорию duplicate",
            action_type="navigate",
            target_kind="tab",
            target_id="Theory",
        ),
    ]

    results = validate_ui_actions(actions, sample_action_indexes())

    assert results[0].ok is True
    assert results[1].ok is False
    assert results[1].duplicate is True
    assert "duplicate action id" in results[1].reason
