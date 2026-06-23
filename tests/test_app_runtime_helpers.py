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


def test_render_html_centralizes_trusted_helper_markup(monkeypatch) -> None:
    calls: list[tuple[str, bool | None]] = []

    def fake_markdown(body: str, unsafe_allow_html: bool | None = None, **_: object) -> None:
        calls.append((body, unsafe_allow_html))

    monkeypatch.setattr(app.st, "markdown", fake_markdown)

    app.render_html(app.render_status_chip("PASS"))

    assert calls == [(app.render_status_chip("PASS"), True)]


def test_render_empty_state_escapes_content_and_uses_card_system() -> None:
    rendered = app.render_empty_state(
        "Нет <данных>",
        "Добавь CSV & нажми scan.",
        action="Открыть <Datasets>",
    )

    assert "console-card" in rendered
    assert "empty-state-card" in rendered
    assert "NEEDS REVIEW" in rendered
    assert "Нет &lt;данных&gt;" in rendered
    assert "CSV &amp; нажми" in rendered
    assert "Открыть &lt;Datasets&gt;" in rendered
    assert "Нет <данных>" not in rendered


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


def sample_note_index() -> tuple[dict[str, str], dict[str, object]]:
    note = {
        "section_key": "00_Atlas",
        "display_name": "00_Knowledge_Map.md",
        "relative_path": "00_Atlas/00_Knowledge_Map.md",
        "path": "/vault/00_Atlas/00_Knowledge_Map.md",
        "stem": "00_Knowledge_Map",
    }
    sections = {"00_Atlas": [note]}
    return note, app.build_note_index(sections)


def test_normalize_theory_note_path_adds_suffix_and_strips_anchor() -> None:
    assert app.normalize_theory_note_path("00 Atlas\\Knowledge Map#section") == "00 Atlas/Knowledge Map.md"
    assert app.normalize_theory_note_path("00_Atlas/00_Knowledge_Map.md") == "00_Atlas/00_Knowledge_Map.md"


def test_find_note_by_path_uses_relative_and_absolute_paths() -> None:
    note, note_index = sample_note_index()

    assert app.find_note_by_path("00_Atlas/00_Knowledge_Map", note_index) is note
    assert app.find_note_by_path("/vault/00_Atlas/00_Knowledge_Map.md", note_index) is note
    assert app.find_note_by_path("missing.md", note_index) is None


def test_open_theory_note_updates_expected_session_keys(monkeypatch) -> None:
    note, note_index = sample_note_index()
    reruns: list[bool] = []
    app.st.session_state.clear()
    app.st.session_state["active_note_path"] = "/vault/Home.md"

    def fake_rerun() -> None:
        reruns.append(True)

    monkeypatch.setattr(app.st, "rerun", fake_rerun)

    app.open_theory_note("00_Atlas/00_Knowledge_Map.md", note_index)

    assert app.st.session_state["active_tab"] == "Theory"
    assert app.st.session_state["active_section"] == "00_Atlas"
    assert app.st.session_state["active_note_path"] == note["path"]
    assert app.st.session_state["note_radio"] == note["path"]
    assert app.st.session_state["section_select"] == "00_Atlas"
    assert app.st.session_state["note_history"] == ["/vault/Home.md"]
    assert reruns == [True]


def test_render_note_link_button_renders_clickable_button_for_existing_note(monkeypatch) -> None:
    _, note_index = sample_note_index()
    buttons: list[dict[str, object]] = []
    captions: list[str] = []

    def fake_button(label: str, **kwargs: object) -> None:
        buttons.append({"label": label, **kwargs})

    monkeypatch.setattr(app.st, "button", fake_button)
    monkeypatch.setattr(app.st, "caption", lambda value: captions.append(str(value)))

    rendered = app.render_note_link_button("Knowledge Map", "00_Atlas/00_Knowledge_Map.md", "outgoing", note_index)

    assert rendered is True
    assert buttons[0]["label"] == "🔗 Knowledge Map"
    assert buttons[0]["help"] == "00_Atlas/00_Knowledge_Map.md"
    assert buttons[0]["on_click"] is app.open_theory_note
    assert captions == ["00_Atlas/00_Knowledge_Map.md"]


def test_render_note_link_button_missing_target_is_static(monkeypatch) -> None:
    _, note_index = sample_note_index()
    buttons: list[str] = []
    html_blocks: list[str] = []

    monkeypatch.setattr(app.st, "button", lambda label, **kwargs: buttons.append(str(label)))
    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))

    rendered = app.render_note_link_button("Missing", "missing_note", "outgoing", note_index)

    assert rendered is False
    assert buttons == []
    assert "Missing — не найдено" in html_blocks[0]
    assert "NEEDS REVIEW" in html_blocks[0]


def test_render_link_card_resolves_outgoing_and_backlink_targets(monkeypatch) -> None:
    note, note_index = sample_note_index()
    calls: list[tuple[str, str]] = []

    def fake_render_note_link_button(label, path, key_prefix, note_index_arg, **kwargs):
        calls.append((str(label), str(path)))
        return True

    monkeypatch.setattr(app, "render_note_link_button", fake_render_note_link_button)

    app.render_link_card({"label": "Knowledge Map", "resolved_note": note, "status": "resolved"}, 0, "outgoing", note_index)
    app.render_link_card({"label": "Backlink", "resolved_note": note, "status": "resolved"}, 1, "backlink", note_index)

    assert calls == [
        ("Knowledge Map", "00_Atlas/00_Knowledge_Map.md"),
        ("Backlink", "00_Atlas/00_Knowledge_Map.md"),
    ]
