from __future__ import annotations

from tools.run_quality_checks import (
    Check,
    CheckResult,
    build_plan,
    has_required_failures,
    parse_args,
)


def ids(mode: str) -> list[str]:
    return [check.check_id for check in build_plan(mode)]  # type: ignore[arg-type]


def test_quick_mode_selects_fast_required_checks() -> None:
    assert ids("quick") == ["compile", "pytest", "app_import", "resources"]


def test_ui_mode_adds_apptest_raw_html_and_e2e() -> None:
    selected = ids("ui")

    assert selected[:4] == ids("quick")
    assert {"apptest", "raw_html", "e2e"}.issubset(selected)


def test_content_mode_adds_gate_link_language_and_sources() -> None:
    selected = ids("content")

    assert selected[:4] == ids("quick")
    assert {"content_gate", "internal_links", "language", "required_sources"}.issubset(selected)


def test_full_mode_includes_smoke_checks_without_duplicate_quick() -> None:
    selected = ids("full")

    assert selected.count("compile") == 1
    assert {"dataset_registry", "mentor_tasks", "df_events_task"}.issubset(selected)


def test_strict_e2e_marks_e2e_required() -> None:
    relaxed = next(check for check in build_plan("ui", strict_e2e=False) if check.check_id == "e2e")
    strict = next(check for check in build_plan("ui", strict_e2e=True) if check.check_id == "e2e")

    assert relaxed.required is False
    assert strict.required is True


def test_dry_run_argument_parses_without_running_checks() -> None:
    args = parse_args(["--mode", "content", "--dry-run"])

    assert args.mode == "content"
    assert args.dry_run is True


def test_required_failures_control_exit_status() -> None:
    required = Check("required", "Required")
    optional = Check("optional", "Optional", required=False)

    assert has_required_failures([CheckResult(required, "FAIL", 1)]) is True
    assert has_required_failures([CheckResult(optional, "FAIL", 1)]) is False
