from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.internal_links import (
    InternalIndexes,
    InternalTarget,
    normalize_identifier,
    validate_internal_target,
)


VALID_ACTION_TYPES = {
    "navigate",
    "set_state",
    "run_check",
    "save_progress",
    "export",
    "open_detail",
}
VALID_TARGET_KINDS = {
    "",
    "tab",
    "theory_note",
    "task",
    "project",
    "milestone",
    "practice",
    "dataset",
    "report",
}


@dataclass(frozen=True)
class UIAction:
    action_id: str
    label: str
    action_type: str
    target_kind: str = ""
    target_id: str = ""
    path: str = ""
    project_id: str = ""
    milestone_id: str = ""
    required_state_keys: tuple[str, ...] = ()
    expected_state_changes: tuple[str, ...] = ()
    safe_to_e2e_click: bool = True
    source: str = ""


@dataclass(frozen=True)
class UIActionIndexes:
    internal: InternalIndexes
    known_state_keys: set[str] = field(default_factory=set)
    tabs: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class UIActionResult:
    action: UIAction
    ok: bool
    reason: str = ""
    severity: str = "pass"
    target_exists: bool = True
    state_keys_ok: bool = True
    duplicate: bool = False


def _missing_state_keys(action: UIAction, known_state_keys: set[str]) -> list[str]:
    return [key for key in action.required_state_keys if key not in known_state_keys]


def _target_result(action: UIAction, indexes: UIActionIndexes) -> tuple[bool, str]:
    target_kind = normalize_identifier(action.target_kind)
    if not target_kind:
        return True, ""
    if target_kind not in VALID_TARGET_KINDS:
        return False, f"unknown target kind: {action.target_kind}"
    if target_kind == "tab":
        target_id = str(action.target_id or "").strip()
        if not target_id:
            return False, "missing tab target"
        if target_id in indexes.tabs:
            return True, ""
        return False, f"tab not found: {target_id}"

    target = InternalTarget(
        kind=target_kind,
        label=action.label,
        target_id=action.target_id,
        path=action.path,
        project_id=action.project_id,
        milestone_id=action.milestone_id,
        source=action.source,
    )
    result = validate_internal_target(target, indexes.internal)
    return result.exists, result.reason


def validate_ui_action(
    action: UIAction,
    indexes: UIActionIndexes,
    known_state_keys: set[str] | None = None,
) -> UIActionResult:
    action_type = normalize_identifier(action.action_type)
    if not action.action_id.strip():
        return UIActionResult(action, False, "missing action id", severity="fail")
    if action_type not in VALID_ACTION_TYPES:
        return UIActionResult(action, False, f"unknown action type: {action.action_type}", severity="fail")

    target_exists, target_reason = _target_result(action, indexes)
    if not target_exists:
        return UIActionResult(
            action,
            False,
            target_reason,
            severity="fail",
            target_exists=False,
        )

    state_keys = known_state_keys if known_state_keys is not None else indexes.known_state_keys
    missing = _missing_state_keys(action, state_keys)
    if missing:
        return UIActionResult(
            action,
            False,
            "missing state keys: " + ", ".join(missing),
            severity="fail",
            state_keys_ok=False,
        )

    if not action.safe_to_e2e_click:
        return UIActionResult(
            action,
            True,
            "unsafe to e2e click; target and state keys validated only",
            severity="warning",
        )

    return UIActionResult(action, True)


def validate_ui_actions(actions: list[UIAction], indexes: UIActionIndexes) -> list[UIActionResult]:
    results: list[UIActionResult] = []
    seen: set[str] = set()
    for action in actions:
        if action.action_id in seen:
            results.append(
                UIActionResult(
                    action,
                    False,
                    f"duplicate action id: {action.action_id}",
                    severity="fail",
                    duplicate=True,
                )
            )
            continue
        seen.add(action.action_id)
        results.append(validate_ui_action(action, indexes))
    return results
