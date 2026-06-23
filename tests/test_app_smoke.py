from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


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
    markers = ("<div", "</div>", "section-eyebrow")
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
