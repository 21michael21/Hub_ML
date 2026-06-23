from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

import app


ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"


@pytest.fixture()
def smoke_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    vault = tmp_path / "vault"
    atlas = vault / "00_Atlas"
    atlas.mkdir(parents=True)
    (vault / "welcome.md").write_text(
        """---
title: Welcome
tags: [smoke]
---

# Welcome

Smoke-test note for Hub_ML.
""",
        encoding="utf-8",
    )
    (atlas / "00_Knowledge_Map.md").write_text(
        """---
title: Knowledge Map
tags: [atlas]
---

# Knowledge Map

[[Welcome]]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("VAULT_PATH", str(vault))
    return vault


def run_app() -> AppTest:
    return AppTest.from_file(str(APP_FILE)).run(timeout=15)


def exception_messages(at: AppTest) -> list[str]:
    return [str(item.value) for item in at.exception]


def markdown_values(at: AppTest) -> list[str]:
    return [str(item.value) for item in at.markdown]


def button_labels(at: AppTest) -> list[str]:
    return [str(item.label) for item in at.button]


def click_button_containing(at: AppTest, text: str) -> AppTest:
    matches = [button for button in at.button if text in str(button.label)]
    assert len(matches) == 1, f"Expected one button containing {text!r}, got {[button.label for button in matches]}"
    matches[0].click()
    return at.run(timeout=15)


def raw_html_markdown_without_allow_html(at: AppTest) -> list[str]:
    markers = ("<div", "</div>", "section-eyebrow", "class=")
    offenders: list[str] = []
    for item in at.markdown:
        value = str(item.value)
        if any(marker in value for marker in markers) and not bool(getattr(item.proto, "allow_html", False)):
            offenders.append(value)
    return offenders


def test_app_home_renders_without_exception(smoke_vault: Path) -> None:
    at = run_app()

    assert not exception_messages(at)
    assert [title.value for title in at.title] == []
    assert "Hub_ML" in " ".join(markdown_values(at))


def test_home_does_not_show_raw_html(smoke_vault: Path) -> None:
    at = run_app()

    assert raw_html_markdown_without_allow_html(at) == []


def test_missing_vault_path_state_is_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VAULT_PATH", raising=False)

    at = run_app()

    assert not exception_messages(at)
    text = " ".join(markdown_values(at))
    assert "Vault не подключён" in text
    assert "VAULT_PATH" in text
    assert "Traceback" not in text


def test_sidebar_or_navigation_has_core_sections(smoke_vault: Path) -> None:
    at = run_app()
    labels = " ".join(button_labels(at))
    sidebar_markdown = " ".join(markdown_values(at.sidebar))

    for expected in ("Home", "Theory", "Practice", "Tasks", "Datasets", "Notebook", "Portfolio"):
        assert expected in labels or expected in sidebar_markdown
    assert "Data Lab" in labels or "Projects" in labels


def test_data_lab_projects_route_does_not_crash(smoke_vault: Path) -> None:
    at = run_app()

    at = click_button_containing(at, "Data Lab")

    assert not exception_messages(at)
    assert any("Data Lab Projects" in value for value in markdown_values(at))


def test_theory_quality_report_view_does_not_crash(smoke_vault: Path) -> None:
    at = run_app()

    at = click_button_containing(at, "Theory Quality")

    assert not exception_messages(at)
    assert any("Theory Quality" in value for value in markdown_values(at))


class FakeExpander:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: object) -> bool:
        return False


def test_theory_quality_missing_reports_state(monkeypatch: pytest.MonkeyPatch) -> None:
    markdown_calls: list[str] = []

    monkeypatch.setattr(app, "load_json_report", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: markdown_calls.append(str(body)))
    monkeypatch.setattr(app.st, "expander", lambda *_args, **_kwargs: FakeExpander())
    monkeypatch.setattr(app.st, "caption", lambda *_args, **_kwargs: None)

    app.render_theory_quality_tab({"all_notes": [], "rel_index": {}, "stem_index": {}})

    rendered = "\n".join(markdown_calls)
    assert "Theory audit report не найден" in rendered
    assert "tools/audit_theory_notes.py" in rendered
    assert "Traceback" not in rendered


def test_experiments_empty_state_is_useful(monkeypatch: pytest.MonkeyPatch) -> None:
    markdown_calls: list[str] = []
    buttons: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: markdown_calls.append(str(body)))
    monkeypatch.setattr(app.st, "button", lambda label, **_kwargs: buttons.append(str(label)) or False)

    app.render_experiments_tab([])

    rendered = "\n".join(markdown_calls)
    assert "Experiment runs не найдены" in rendered
    assert "Open ML Lab" in buttons
    assert "Traceback" not in rendered


def test_task_result_rendering_shows_status_chips(monkeypatch: pytest.MonkeyPatch) -> None:
    markdown_calls: list[tuple[str, bool | None]] = []
    feedback: list[str] = []

    def fake_markdown(body: str, unsafe_allow_html: bool | None = None, **_: Any) -> None:
        markdown_calls.append((str(body), unsafe_allow_html))

    monkeypatch.setattr(app.st, "markdown", fake_markdown)
    monkeypatch.setattr(app.st, "success", lambda body, **_kwargs: feedback.append(str(body)))
    monkeypatch.setattr(app.st, "error", lambda body, **_kwargs: feedback.append(str(body)))
    monkeypatch.setattr(app.st, "warning", lambda body, **_kwargs: feedback.append(str(body)))
    monkeypatch.setattr(app.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app.st, "code", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app.st, "expander", lambda *_args, **_kwargs: FakeExpander())

    for classification in ("PASS", "FAIL", "ERROR"):
        app.render_mentor_task_result(
            {
                "classification": classification,
                "elapsed": 0.01,
                "stdout": "",
                "outputs": [],
            }
        )

    rendered = "\n".join(body for body, _ in markdown_calls)
    assert "chip-pass" in rendered
    assert "chip-fail" in rendered
    assert "chip-error" in rendered
    assert any("Решено" in item for item in feedback)
    assert any("FAIL" in item for item in feedback)
    assert any("ERROR" in item for item in feedback)
    assert all(unsafe is True for body, unsafe in markdown_calls if "<div" in body)


def test_project_checklist_empty_and_present_states(monkeypatch: pytest.MonkeyPatch) -> None:
    markdown_calls: list[str] = []
    checkbox_keys: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: markdown_calls.append(str(body)))
    monkeypatch.setattr(app.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app.st, "checkbox", lambda _label, value=False, key=None, **_kwargs: checkbox_keys.append(str(key)) or value)

    project = {"id": "project/one"}
    empty_milestone = {"id": "load/data", "checklist": []}
    checked_milestone = {"id": "load/data", "checklist": ["Load data", "Check columns"]}

    app.render_project_checklist(project, empty_milestone, {})
    assert checkbox_keys == []

    app.render_project_checklist(project, checked_milestone, {"checked_items": ["Load data"]})
    assert "##### Checklist" in markdown_calls
    assert checkbox_keys == [
        "project_milestone_project_one_load_data_check_0",
        "project_milestone_project_one_load_data_check_1",
    ]
    assert len(set(checkbox_keys)) == len(checkbox_keys)


def test_navigation_labels_include_major_sections_and_russian_home_labels(smoke_vault: Path) -> None:
    at = run_app()
    visible = " ".join(markdown_values(at))
    labels = " ".join(button_labels(at))
    combined = f"{visible} {labels}"

    for expected in (
        "Home",
        "Theory",
        "Practice",
        "Theory Quality",
        "Roadmap",
        "Progress",
        "Data Lab",
        "ML Lab",
        "Notebook",
        "Datasets",
        "Tasks",
        "Algorithms",
        "Interviews",
        "Portfolio",
        "Experiments",
        "Architecture",
        "Links Health",
    ):
        assert expected in combined

    assert "Продолжить" in visible
    assert "План на сегодня" in visible
    assert "Статус" in visible
    assert "Resume" not in visible
    assert "Today" not in visible
