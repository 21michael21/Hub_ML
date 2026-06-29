from __future__ import annotations

import json

import app


class FakeColumn:
    def __enter__(self) -> "FakeColumn":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


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


def test_status_chip_is_static_not_clickable() -> None:
    rendered = app.render_status_chip("PASS")

    assert "status-chip" in rendered
    assert "static-chip" in rendered
    assert "clickable-card" not in rendered
    assert "<button" not in rendered


def test_render_flat_section_header_uses_no_card_wrapper() -> None:
    rendered = app.render_flat_section_header(
        "Theory Quality",
        "Read-only срез качества базы знаний.",
        eyebrow="Learn",
        status="READY",
        caption="audit · vault",
    )

    assert "flat-section-header" in rendered
    assert "console-card" not in rendered
    assert "Theory Quality" in rendered
    assert "audit · vault" in rendered
    assert "READY" in rendered


def test_render_metric_tile_omits_progress_bar_for_plain_counts() -> None:
    rendered = app.render_metric_tile("Без sources", 3, status="NEEDS REVIEW")

    assert "metric-tile" in rendered
    assert "metric-bar" not in rendered


def test_theory_note_query_href_encodes_note_path() -> None:
    href = app.theory_note_query_href("00 Atlas/A&B.md")

    assert href == "?tab=Theory&note=00%20Atlas%2FA%26B.md"


def test_render_clickable_row_is_single_anchor_card() -> None:
    rendered = app.render_clickable_row(
        "Weak <Note>",
        "score: 10 · words: 20",
        href=app.theory_note_query_href("00_Atlas/Weak.md"),
        action="Открыть",
        status="FAIL",
        accent="fail",
    )

    assert rendered.startswith('<a class="clickable-row clickable-row-fail"')
    assert 'href="?tab=Theory&amp;note=00_Atlas%2FWeak.md"' in rendered
    assert "Weak &lt;Note&gt;" in rendered
    assert "→ Открыть" in rendered
    assert "<button" not in rendered
    assert rendered.count("<a ") == 1


def test_internal_target_query_href_encodes_task_target() -> None:
    target = app.InternalTarget(
        kind="task",
        label="Task <One>",
        target_id="python/basics",
        exists=True,
    )

    href = app.internal_target_query_href(target)

    assert href == "?tab=%F0%9F%8E%AF%20Tasks&kind=task&target=python%2Fbasics"


def test_render_internal_action_row_is_single_anchor_card() -> None:
    target = app.InternalTarget(
        kind="task",
        label="Task <One>",
        target_id="python/basics",
        exists=True,
    )

    rendered = app.render_internal_action_row(
        target,
        "Advanced <Python>",
        "задача · confidence high",
        "IN PROGRESS",
        "Открыть",
    )

    assert rendered.startswith('<a class="clickable-row"')
    assert 'href="?tab=%F0%9F%8E%AF%20Tasks&amp;kind=task&amp;target=python%2Fbasics"' in rendered
    assert "Advanced &lt;Python&gt;" in rendered
    assert "Task &lt;One&gt;" not in rendered
    assert "→ Открыть" in rendered
    assert "<button" not in rendered
    assert rendered.count("<a ") == 1


def test_apply_query_param_navigation_opens_internal_target(monkeypatch) -> None:
    values = {
        "tab": "🎯 Tasks",
        "kind": "task",
        "target": "python/basics",
        "project": "",
        "milestone": "",
        "source": "",
        "note": "",
    }
    opened: list[tuple[app.InternalTarget, bool]] = []

    monkeypatch.setattr(app, "query_param_value", lambda name: values.get(name, ""))
    monkeypatch.setattr(app, "open_internal_target", lambda target, rerun=True: opened.append((target, rerun)))
    app.st.session_state.pop("_last_query_nav", None)

    app.apply_query_param_navigation({"all_notes": [], "rel_index": {}, "stem_index": {}})

    assert len(opened) == 1
    target, rerun = opened[0]
    assert target.kind == "task"
    assert target.target_id == "python/basics"
    assert target.exists is True
    assert rerun is False


def test_home_dashboard_primary_actions_use_clickable_rows(monkeypatch) -> None:
    html_blocks: list[str] = []
    buttons: list[str] = []
    note = {
        "section_key": "00_Atlas",
        "display_name": "Knowledge Map.md",
        "relative_path": "00_Atlas/Knowledge Map.md",
        "path": "/vault/00_Atlas/Knowledge Map.md",
        "stem": "Knowledge Map",
    }
    task = {
        "id": "advanced_python",
        "title": "Advanced Python",
        "confidence": "high",
        "notebook_label": "задача",
    }

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: html_blocks.append(str(body)))
    monkeypatch.setattr(app.st, "button", lambda label, **_kwargs: buttons.append(str(label)) or False)
    monkeypatch.setattr(app.st, "columns", lambda count: [FakeColumn() for _ in range(count)])
    monkeypatch.setattr(app, "ensure_progress_state", lambda: {"notes": {}, "mentor_tasks_status": {}})
    monkeypatch.setattr(
        app,
        "content_gate_home_summary",
        lambda: {"percent": 100, "passed": 36, "total": 36, "status": "PASS", "caption": "Все темы прошли контроль качества."},
    )

    app.render_dashboard(
        {"00_Atlas": [note]},
        [],
        [],
        {"summary": {"broken": 0}},
        {"tasks": [task]},
        [],
        [],
        {},
        {"summary": {"average_quality_score": 54.5, "weakest_notes": []}},
        {"summary": {}},
    )

    rendered = "\n".join(html_blocks)
    assert "home-quality-gate" in rendered
    assert "QUALITY GATE" in rendered
    assert "36<span" in rendered
    assert "clickable-row-list home-action-list" in rendered
    assert "Открыть задачу" not in buttons
    assert "Открыть теорию" not in buttons


def test_content_gate_home_summary_parses_complete_report(tmp_path) -> None:
    report = tmp_path / "content_gate_report.json"
    report.write_text(
        json.dumps(
            {
                "summary": {"passed_topics": 36, "total_topics": 36},
            }
        ),
        encoding="utf-8",
    )

    summary = app.content_gate_home_summary(report)

    assert summary == {
        "percent": 100,
        "passed": 36,
        "total": 36,
        "status": "PASS",
        "caption": "Все 36 тем прошли контроль качества контента.",
    }


def test_inline_wikilink_renders_as_static_chip_not_fake_button() -> None:
    rendered = app.render_markdown_with_wikilinks("Смотри [[A & B]].")

    assert "obsidian-link-static" in rendered
    assert "static-chip" in rendered
    assert "obsidian-link\"" not in rendered
    assert "<button" not in rendered
    assert "A &amp; B" in rendered


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


def test_theory_internal_target_opens_by_path_not_display_label(monkeypatch) -> None:
    note, note_index = sample_note_index()
    reruns: list[bool] = []
    app.st.session_state.clear()
    app.st.session_state["home_note_index"] = note_index
    app.st.session_state["active_note_path"] = "/vault/Home.md"

    monkeypatch.setattr(app.st, "rerun", lambda: reruns.append(True))

    target = app.InternalTarget(
        kind="theory_note",
        label="00 Atlas / 00_Knowledge_Map.md",
        path="00_Atlas/00_Knowledge_Map.md",
        target_id="00_Atlas/00_Knowledge_Map.md",
    )

    app.open_internal_target(target)

    assert app.st.session_state["active_tab"] == "Theory"
    assert app.st.session_state["active_note_path"] == note["path"]
    assert app.st.session_state["note_radio"] == note["path"]
    assert reruns == [True]


def test_task_internal_target_opens_selected_task(monkeypatch) -> None:
    reruns: list[bool] = []
    app.st.session_state.clear()
    monkeypatch.setattr(app.st, "rerun", lambda: reruns.append(True))

    app.open_internal_target(app.InternalTarget(kind="task", label="Python", target_id="python_basics_records"))

    assert app.st.session_state["active_tab"] == "🎯 Tasks"
    assert app.st.session_state["selected_mentor_task"] == "python_basics_records"
    assert app.st.session_state["mentor_task_notebook_filter"] == "Все"
    assert app.st.session_state["mentor_task_confidence_filter"] == "Все"
    assert reruns == [True]


def test_project_milestone_internal_target_opens_project_and_milestone(monkeypatch) -> None:
    reruns: list[bool] = []
    app.st.session_state.clear()
    monkeypatch.setattr(app.st, "rerun", lambda: reruns.append(True))

    app.open_internal_target(
        app.InternalTarget(
            kind="milestone",
            label="Define target",
            target_id="orders_conversion_baseline::define_target",
            project_id="orders_conversion_baseline",
            milestone_id="define_target",
            source="ml_lab",
        )
    )

    assert app.st.session_state["active_tab"] == "🤖 ML Lab"
    assert app.st.session_state["selected_data_lab_project"] == "orders_conversion_baseline"
    assert app.st.session_state["selected_project_milestone"] == "define_target"
    assert reruns == [True]


def test_invalid_internal_target_does_not_rerun(monkeypatch) -> None:
    reruns: list[bool] = []
    app.st.session_state.clear()
    monkeypatch.setattr(app.st, "rerun", lambda: reruns.append(True))

    app.open_internal_target(
        app.InternalTarget(
            kind="task",
            label="Missing task",
            target_id="missing",
            exists=False,
            disabled_reason="missing target",
        )
    )

    assert "active_tab" not in app.st.session_state
    assert reruns == []


def test_render_internal_action_card_disables_invalid_target(monkeypatch) -> None:
    buttons: list[dict[str, object]] = []
    captions: list[str] = []
    html_blocks: list[str] = []

    def fake_button(label: str, **kwargs: object) -> bool:
        buttons.append({"label": label, **kwargs})
        return False

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app.st, "button", fake_button)
    monkeypatch.setattr(app.st, "caption", lambda value: captions.append(str(value)))

    target = app.InternalTarget(
        kind="theory_note",
        label="Missing note",
        path="missing.md",
        exists=False,
        disabled_reason="Заметка не найдена: missing.md",
    )

    assert app.render_internal_action_card(target, "Missing", "missing.md", "TODO", "test_action") is False
    assert buttons[0]["disabled"] is True
    assert buttons[0]["on_click"] is None
    assert captions == ["Заметка не найдена: missing.md"]
    assert "Missing" in html_blocks[0]
    assert "disabled-target-card" in html_blocks[0]


def test_render_internal_action_card_marks_clickable_target(monkeypatch) -> None:
    buttons: list[dict[str, object]] = []
    html_blocks: list[str] = []

    def fake_button(label: str, **kwargs: object) -> bool:
        buttons.append({"label": label, **kwargs})
        return False

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app.st, "button", fake_button)

    target = app.InternalTarget(
        kind="task",
        label="Task",
        target_id="python_basics_records",
        exists=True,
    )

    assert app.render_internal_action_card(target, "Task", "Open task", "TODO", "test_action", "Открыть задачу") is False
    assert "internal-action-card clickable-card" in html_blocks[0]
    assert buttons[0]["label"] == "Открыть задачу"
    assert buttons[0]["disabled"] is False
    assert buttons[0]["on_click"] is app.open_internal_target_fields


def test_content_gate_status_renders_31_of_36(tmp_path) -> None:
    report = tmp_path / "content_gate_report.json"
    report.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-23T09:00:00+00:00",
                "summary": {"passed_topics": 31, "total_topics": 36},
            }
        ),
        encoding="utf-8",
    )

    assert app.content_gate_status(report) == "Gate: 31/36 · отчёт 2026-06-23"


def test_content_gate_status_renders_36_of_36(tmp_path) -> None:
    report = tmp_path / "content_gate_report.json"
    report.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-23T09:00:00+00:00",
                "summary": {"passed_topics": 36, "total_topics": 36},
            }
        ),
        encoding="utf-8",
    )

    assert app.content_gate_status(report) == "Gate: 36/36 · отчёт 2026-06-23"


def test_content_gate_status_missing_report_is_unknown(tmp_path) -> None:
    assert app.content_gate_status(tmp_path / "missing.json") == "Gate: нет отчёта"


def test_content_gate_status_malformed_report_does_not_crash(tmp_path) -> None:
    report = tmp_path / "content_gate_report.json"
    report.write_text("{not-json", encoding="utf-8")

    assert app.content_gate_status(report) == "Gate: отчёт повреждён"
