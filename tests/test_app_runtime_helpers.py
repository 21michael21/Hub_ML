from __future__ import annotations

import app


def test_safe_widget_key_accepts_two_and_four_parts() -> None:
    assert app.safe_widget_key("portfolio_output", "card 1") == "portfolio_output_card_1"
    assert (
        app.safe_widget_key("project_milestone", "orders/project", "load data", "check 1")
        == "project_milestone_orders_project_load_data_check_1"
    )


def test_safe_widget_key_handles_empty_and_long_values() -> None:
    assert app.safe_widget_key("", None) == "widget"

    long_value = "x" * 180
    first = app.safe_widget_key("prefix", long_value)
    second = app.safe_widget_key("prefix", long_value)

    assert first == second
    assert len(first) <= 110
    assert first.startswith("prefix_")
    assert first.rsplit("_", 1)[-1].isalnum()


def test_project_milestone_widget_key_is_stable() -> None:
    first = app.project_milestone_widget_key("orders/conversion", "define target", "code")
    second = app.project_milestone_widget_key("orders/conversion", "define target", "code")

    assert first == second
    assert first == "project_milestone_orders_conversion_define_target_code"


def test_render_section_eyebrow_block_uses_html_markdown(monkeypatch) -> None:
    calls: list[tuple[str, bool | None]] = []

    def fake_markdown(body: str, unsafe_allow_html: bool | None = None, **_: object) -> None:
        calls.append((body, unsafe_allow_html))

    monkeypatch.setattr(app.st, "markdown", fake_markdown)

    app.render_section_eyebrow_block("Resume")

    assert calls == [(app.render_section_eyebrow("Resume"), True)]


def test_home_note_target_uses_relative_path_not_display_label() -> None:
    note = {
        "section_label": "00 Atlas",
        "display_name": "00_Knowledge_Map.md",
        "relative_path": "00_Atlas/00_Knowledge_Map.md",
        "path": "/vault/00_Atlas/00_Knowledge_Map.md",
    }

    target = app.normalize_home_note_target(note)

    assert target["label"] == "00 Atlas / 00_Knowledge_Map.md"
    assert target["path"] == "00_Atlas/00_Knowledge_Map.md"
    assert target["tab"] == "Theory"


def test_note_from_relative_path_in_sections() -> None:
    note = {
        "section_key": "00_Atlas",
        "section_label": "00 Atlas",
        "display_name": "00_Knowledge_Map.md",
        "relative_path": "00_Atlas/00_Knowledge_Map.md",
        "path": "/vault/00_Atlas/00_Knowledge_Map.md",
    }
    sections = {"00_Atlas": [note]}

    assert app.note_from_relative_path_in_sections("00_Atlas/00_Knowledge_Map.md", sections) is note
    assert app.note_from_relative_path_in_sections("00 Atlas / 00_Knowledge_Map.md", sections) is None
