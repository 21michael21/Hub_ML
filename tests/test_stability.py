from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

import app
from core.projects.loader import load_project_recipes
from core.reports.theory_quality import load_json_report
from core.tasks.loader import load_mentor_tasks


ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"


def run_app() -> AppTest:
    return AppTest.from_file(str(APP_FILE)).run(timeout=15)


def exception_messages(at: AppTest) -> list[str]:
    return [str(item.value) for item in at.exception]


def markdown_text(at: AppTest) -> str:
    return " ".join(str(item.value) for item in at.markdown)


def test_app_without_vault_path_shows_setup_card(monkeypatch) -> None:
    monkeypatch.delenv("VAULT_PATH", raising=False)

    at = run_app()

    assert not exception_messages(at)
    text = markdown_text(at)
    assert "Vault не подключён" in text
    assert "VAULT_PATH" in text


def test_app_with_missing_vault_path_shows_error_card(monkeypatch, tmp_path: Path) -> None:
    missing_vault = tmp_path / "missing-vault"
    monkeypatch.setenv("VAULT_PATH", str(missing_vault))

    at = run_app()

    assert not exception_messages(at)
    text = markdown_text(at)
    assert "Vault не найден" in text
    assert str(missing_vault) in text


def test_safe_loaders_return_empty_defaults_for_missing_paths(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    assert app.scan_vault(str(missing)) == {}
    assert app.scan_link_graph(str(missing)) == app.empty_link_graph()
    assert load_json_report(missing / "report.json") == {}
    assert load_project_recipes(missing / "projects") == []
    assert load_mentor_tasks(missing / "mentor_tasks.json") == {"tasks": [], "skipped": 0}


def test_theory_quality_missing_reports_do_not_raise(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(app, "THEORY_AUDIT_REPORT_PATH", tmp_path / "missing_theory_audit.json")
    monkeypatch.setattr(app, "COVERAGE_REPORT_PATH", tmp_path / "missing_coverage_report.json")
    monkeypatch.setattr(app, "CONTENT_GATE_REPORT_PATH", tmp_path / "missing_content_gate.json")

    app.render_theory_quality_tab({"all_notes": [], "rel_index": {}, "stem_index": {}})


def test_home_renders_with_empty_data() -> None:
    app.render_dashboard(
        sections={},
        practice_cards=[],
        datasets=[],
        graph=app.empty_link_graph(),
        mentor_data={"tasks": [], "skipped": 0},
        data_lab_projects=[],
        algorithm_lessons=[],
        interview_data={"companies": [], "total_companies": 0},
        audit_report={},
        coverage_report={},
    )
