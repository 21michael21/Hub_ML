from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import app


class FakeColumn:
    def __enter__(self) -> "FakeColumn":
        return self

    def __exit__(self, *_: object) -> bool:
        return False

    def button(self, *_args: object, **_kwargs: object) -> bool:
        return False


def runtime_sample_project() -> dict[str, object]:
    return {
        "id": "orders_eda",
        "title": "Orders EDA",
        "level": "beginner",
        "track": "Data Lab",
        "datasets": ["df_orders.csv"],
        "skills": ["pandas", "eda"],
        "estimated_time": "2 ч",
        "goal": "Build an EDA report.",
        "business_context": "Understand orders.",
        "prerequisites": ["Pandas basics"],
        "related_theory_paths": ["02_Data_Analysis/Pandas.md"],
        "related_practice_ids": ["orders_practice"],
        "related_task_ids": ["analysis_3_pandas"],
        "related_dataset_names": ["df_orders.csv"],
        "milestones": [
            {
                "id": "load",
                "title": "Load data",
                "type": "code",
                "description": "Load the CSV.",
                "required": True,
                "portfolio_output": "Dataset overview",
            },
            {
                "id": "summary",
                "title": "Write summary",
                "type": "report",
                "description": "Write the result.",
                "required": True,
                "portfolio_output": "Mini report",
            },
            {
                "id": "optional_card",
                "title": "Optional model card",
                "type": "model_card",
                "description": "Optional reflection.",
                "required": False,
            },
        ],
        "deliverables": ["Report"],
        "portfolio_prompt": "Explain the analysis.",
    }


def test_safe_widget_key_accepts_two_and_four_parts() -> None:
    assert app.safe_widget_key("portfolio_output", "card 1") == "portfolio_output_card_1"
    assert (
        app.safe_widget_key("project_milestone", "orders/project", "load data", "check 1")
        == "project_milestone_orders_project_load_data_check_1"
    )


def test_env_path_uses_override_and_expands_user(monkeypatch, tmp_path) -> None:
    override = tmp_path / "progress.json"
    monkeypatch.setenv("HUB_ML_PROGRESS_PATH", str(override))

    assert app.env_path("HUB_ML_PROGRESS_PATH", "~/fallback.json") == override


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


def test_find_next_lab_milestone_prefers_required_todo() -> None:
    project = runtime_sample_project()
    record = {"milestones": {"load": {"done": True}}}

    milestone = app.find_next_lab_milestone(project, record)

    assert milestone is not None
    assert milestone["id"] == "summary"


def test_find_next_lab_milestone_falls_back_to_optional() -> None:
    project = runtime_sample_project()
    record = {"milestones": {"load": {"done": True}, "summary": {"done": True}}}

    milestone = app.find_next_lab_milestone(project, record)

    assert milestone is not None
    assert milestone["id"] == "optional_card"


def test_render_lab_project_catalog_card_marks_selected() -> None:
    rendered = app.render_lab_project_catalog_card(
        runtime_sample_project(),
        {"done": 1, "total": 3, "ratio": 1 / 3, "complete": False},
        selected=True,
        source="data_lab",
    )

    assert rendered.startswith('<a class="lab-project-card lab-project-card-selected"')
    assert "href=\"?tab=%F0%9F%A7%AA%20Data%20Lab%20Projects&amp;kind=project&amp;target=orders_eda&amp;project=orders_eda&amp;source=data_lab\"" in rendered
    assert "Orders EDA" in rendered
    assert "lab-project-progress" in rendered
    assert "1/3" in rendered
    assert "pandas · eda" in rendered
    assert "→ Выбран" in rendered
    assert "<button" not in rendered


def test_render_lab_project_catalog_card_uses_ml_lab_query_target() -> None:
    rendered = app.render_lab_project_catalog_card(
        runtime_sample_project() | {"track": "Classic ML"},
        {"done": 0, "total": 3, "ratio": 0, "complete": False},
        selected=False,
        source="ml_lab",
    )

    assert rendered.startswith('<a class="lab-project-card"')
    assert "href=\"?tab=%F0%9F%A4%96%20ML%20Lab&amp;kind=project&amp;target=orders_eda&amp;project=orders_eda&amp;source=ml_lab\"" in rendered
    assert "→ Открыть проект" in rendered
    assert "<button" not in rendered


def test_render_lab_next_action_is_attached_clickable_card(monkeypatch) -> None:
    html_blocks: list[str] = []
    action_buttons: list[str] = []
    project = runtime_sample_project()
    milestone = project["milestones"][1]

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app, "render_action_button", lambda label, **_kwargs: action_buttons.append(str(label)) or False)

    app.render_lab_next_action(project, milestone, {"done": 1, "total": 3})

    rendered = "\n".join(html_blocks)
    assert rendered.startswith('<a class="lab-next-action"')
    assert "href=\"?tab=%F0%9F%A7%AA%20Data%20Lab%20Projects&amp;kind=milestone&amp;target=orders_eda%3A%3Asummary&amp;project=orders_eda&amp;milestone=summary&amp;source=data_lab\"" in rendered
    assert "Следующий шаг: Write summary" in rendered
    assert "→ Открыть следующий шаг" in rendered
    assert action_buttons == []
    assert "<button" not in rendered


def test_build_lab_prerequisite_groups_renders_missing_targets_disabled() -> None:
    project = runtime_sample_project()

    groups = app.build_lab_prerequisite_groups(
        project,
        note_index={},
        practice_cards=[],
        mentor_tasks=[],
        datasets=[],
    )

    flat_items = [item for group in groups for item in group["items"]]
    assert [group["title"] for group in groups] == [
        "Теория",
        "Практика",
        "Задачи",
        "Датасеты",
        "Что нужно закрыть",
    ]
    assert any(item["label"] == "02_Data_Analysis/Pandas.md" and item["disabled"] for item in flat_items)
    assert any("Заметка не найдена" in item["reason"] for item in flat_items)
    assert any(item["label"] == "df_orders.csv" and item["disabled"] for item in flat_items)


def test_render_lab_prerequisite_item_uses_button_state(monkeypatch) -> None:
    buttons: list[dict[str, object]] = []
    captions: list[str] = []
    html_blocks: list[str] = []

    def fake_button(label: str, **kwargs: object) -> bool:
        buttons.append({"label": label, **kwargs})
        return False

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app.st, "button", fake_button)
    monkeypatch.setattr(app.st, "caption", lambda value: captions.append(str(value)))

    app.render_lab_prerequisite_item(
        {
            "label": "Missing dataset",
            "meta": "датасет",
            "status": "BLOCKED",
            "button_label": "Открыть датасет",
            "disabled": True,
            "reason": "Датасет не найден",
            "target": None,
        },
        "lab_prereq_test",
    )

    assert "lab-prerequisite-row" in html_blocks[0]
    assert buttons[0]["label"] == "Открыть датасет"
    assert buttons[0]["disabled"] is True
    assert buttons[0]["on_click"] is None
    assert captions == ["Датасет не найден"]


def test_render_lab_milestone_summary_uses_ordered_russian_step_labels(monkeypatch) -> None:
    html_blocks: list[str] = []
    project = runtime_sample_project()
    milestone = project["milestones"][0]

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))

    app.render_lab_milestone_summary(project, milestone, index=2, done=False, current=True)

    rendered = "\n".join(html_blocks)
    assert "lab-milestone-current" in rendered
    assert "Шаг 2" in rendered
    assert "обязательный" in rendered
    assert "текущий шаг" in rendered
    assert "Ожидаемый результат" in rendered


def test_render_data_lab_project_detail_uses_learning_flow_sections(monkeypatch) -> None:
    html_blocks: list[str] = []
    section_labels: list[str] = []
    markdown_blocks: list[str] = []
    project = runtime_sample_project()

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app, "render_section_eyebrow_block", lambda label: section_labels.append(str(label)))
    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: markdown_blocks.append(str(body)))
    monkeypatch.setattr(app.st, "button", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(app.st, "columns", lambda count, **_kwargs: [FakeColumn() for _ in range(count if isinstance(count, int) else len(count))])
    monkeypatch.setattr(app.st, "expander", lambda *_args, **_kwargs: FakeColumn())
    monkeypatch.setattr(app.st, "checkbox", lambda *_args, **kwargs: bool(kwargs.get("value", False)))
    monkeypatch.setattr(app.st, "text_area", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(app.st, "caption", lambda value: markdown_blocks.append(str(value)))
    monkeypatch.setattr(app.st, "code", lambda value, **_kwargs: markdown_blocks.append(str(value)))
    monkeypatch.setattr(app, "get_data_lab_project_record", lambda _project_id: {})
    monkeypatch.setattr(app, "get_data_lab_milestone_record", lambda _project_id, _milestone_id: {})
    monkeypatch.setattr(app, "is_data_lab_milestone_done", lambda _project_id, _milestone_id: False)
    monkeypatch.setattr(app, "render_project_code_runner", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app, "render_project_writing_milestone", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app, "render_project_workspace_scaffolder", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app, "render_experiment_tracker", lambda *_args, **_kwargs: section_labels.append("Эксперименты"))
    monkeypatch.setattr(app, "render_data_lab_project_completion", lambda *_args, **_kwargs: None)

    app.render_data_lab_project_detail(project, [], [], [], {})

    rendered = "\n".join(html_blocks + markdown_blocks + section_labels)
    assert "lab-detail-flow" in rendered
    assert "Обзор проекта" in section_labels
    assert "Перед стартом" in section_labels
    assert "База перед проектом" in section_labels
    assert "Шаги проекта" in section_labels
    assert "Portfolio output" in section_labels
    assert "Milestones" not in section_labels
    assert "Prerequisites" not in section_labels


def test_render_data_lab_projects_tab_renders_catalog_and_selected_detail(monkeypatch) -> None:
    html_blocks: list[str] = []
    markdown_blocks: list[str] = []
    buttons: list[str] = []
    selected_details: list[str] = []
    first = runtime_sample_project()
    second = runtime_sample_project() | {"id": "orders_ml", "title": "Orders ML", "track": "Classic ML"}

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: markdown_blocks.append(str(body)))
    monkeypatch.setattr(app.st, "button", lambda label, **_kwargs: buttons.append(str(label)) or False)
    monkeypatch.setattr(app.st, "columns", lambda *_args, **_kwargs: [FakeColumn(), FakeColumn()])
    monkeypatch.setattr(app, "get_data_lab_project_record", lambda _project_id: {})
    monkeypatch.setattr(
        app,
        "render_data_lab_project_detail",
        lambda project, *_args, **_kwargs: selected_details.append(str(project["id"])),
    )
    app.st.session_state.clear()

    app.render_data_lab_projects_tab([first, second], [], [], [], {}, title="Data Lab")

    rendered = "\n".join(html_blocks + markdown_blocks)
    assert "flat-section-header" in rendered
    assert "lab-project-card-selected" in rendered
    assert "lab-project-card-action" in rendered
    assert "Каталог проектов" in rendered
    assert buttons == []
    assert selected_details == ["orders_eda"]


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


def test_injected_css_has_visual_polish_accessibility_contract(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: calls.append(str(body)))

    app.inject_styles()

    css = "\n".join(calls)
    assert "@keyframes sectionFade" in css
    assert ".section-fade" in css
    assert ".ui-state-card" in css
    assert ".kernel-busy-state" in css
    assert ".task-result-state" in css
    assert "prefers-reduced-motion" in css
    assert ":focus-visible" in css
    assert "transition: width var(--duration-slow)" in css


def test_injected_css_has_spacing_motion_responsive_polish(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: calls.append(str(body)))

    app.inject_styles()

    css = "\n".join(calls)
    assert "--section-gap:32px" in css
    assert "--card-padding:18px" in css
    assert "padding: clamp(24px, 3vw, 40px)" in css
    assert ".page-shell > .section-fade + .section-fade" in css
    assert ".ui-state-card .console-card-eyebrow::before" in css
    assert "width: 38px" in css
    assert "opacity: 0.68" in css
    assert ".lab-prerequisite-row" in css
    assert "padding: 16px 18px" in css
    assert ".lab-catalog-column" in css
    assert "position: static" in css


def test_normalize_layout_mode_accepts_known_modes() -> None:
    assert app.normalize_layout_mode("reading") == "reading"
    assert app.normalize_layout_mode("dashboard") == "dashboard"
    assert app.normalize_layout_mode("workbench") == "workbench"
    assert app.normalize_layout_mode("full_workspace") == "full_workspace"


def test_normalize_layout_mode_falls_back_to_dashboard() -> None:
    assert app.normalize_layout_mode("wide-ish") == "dashboard"
    assert app.normalize_layout_mode("") == "dashboard"


def test_layout_mode_for_tab_maps_workspace_pages() -> None:
    assert app.layout_mode_for_tab("Home") == "dashboard"
    assert app.layout_mode_for_tab("Theory") == "reading"
    assert app.layout_mode_for_tab("🎯 Tasks") == "workbench"
    assert app.layout_mode_for_tab("🧪 Data Lab Projects") == "workbench"
    assert app.layout_mode_for_tab("🤖 ML Lab") == "workbench"
    assert app.layout_mode_for_tab("📓 Notebook") == "full_workspace"


def test_learner_navigation_shows_only_learning_loop() -> None:
    visible = app.visible_nav_tabs("learner")

    assert visible == [
        "Home",
        "Theory",
        "🎯 Practice",
        "🎯 Tasks",
        "🧪 Data Lab Projects",
        "🤖 ML Lab",
        "📓 Notebook",
        "📁 Portfolio",
    ]
    assert len(visible) == 8
    assert "🧭 Theory Quality" not in visible
    assert "Roadmap" not in visible
    assert "Progress" not in visible


def test_admin_navigation_shows_every_tab_and_deep_links_stay_available() -> None:
    admin_tabs = app.visible_nav_tabs("admin")

    assert admin_tabs == app.TAB_OPTIONS
    assert "🧭 Theory Quality" in admin_tabs
    assert "Roadmap" in admin_tabs
    assert "Progress" in admin_tabs
    assert "🧭 Theory Quality" in app.TAB_OPTIONS
    assert app.normalize_nav_mode("unknown") == "learner"


def test_page_layout_css_reduces_one_size_global_constraint() -> None:
    dashboard_css = app.page_layout_mode_css("dashboard")
    workbench_css = app.page_layout_mode_css("workbench")
    full_css = app.page_layout_mode_css("full_workspace")

    assert "1280px" in dashboard_css
    assert "1440px" in workbench_css
    assert "max-width: none" in full_css
    assert "980px" not in dashboard_css
    assert "[data-testid=\"stMainBlockContainer\"]" in workbench_css


def test_render_page_shell_helpers_emit_safe_classes() -> None:
    start = app.render_page_shell_start("reading", "Theory Page")
    end = app.render_page_shell_end()

    assert start == '<div class="page-shell page-shell-reading theory-page">'
    assert end == "</div>"
    assert "<script" not in start
    assert "Theory Page" not in start


def test_theory_layout_css_uses_article_and_side_panel(monkeypatch) -> None:
    rendered: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: rendered.append(str(body)))

    app.inject_styles()

    css = "\n".join(rendered)
    assert ".theory-note-layout" in css
    assert ".theory-main" in css
    assert "max-width: min(100%, 1380px)" in css
    assert "max-width: 820px" in css
    assert "minmax(320px, 380px)" in css
    assert "max-width: 1120px" not in css
    assert "@media (max-width: 900px)" in css
    assert "position: static" in css


def test_status_chip_is_static_not_clickable() -> None:
    rendered = app.render_status_chip("PASS")

    assert "status-chip" in rendered
    assert "static-chip" in rendered
    assert "clickable-card" not in rendered
    assert "<button" not in rendered


def test_static_chip_is_metadata_only() -> None:
    rendered = app.render_static_chip("level", "beginner")

    assert "static-chip" in rendered
    assert 'aria-disabled="true"' in rendered
    assert "clickable" not in rendered
    assert "<button" not in rendered
    assert "level" in rendered
    assert "beginner" in rendered


def test_disabled_chip_includes_visible_reason() -> None:
    rendered = app.render_disabled_chip("Dataset", "Файл не найден")

    assert "disabled-chip" in rendered
    assert "aria-disabled=\"true\"" in rendered
    assert "Dataset" in rendered
    assert "Файл не найден" in rendered
    assert "<button" not in rendered


def test_render_action_button_requires_action_target(monkeypatch) -> None:
    with pytest.raises(ValueError, match="requires on_click or href"):
        app.render_action_button("Открыть", key="missing_action")


def test_ui_component_rules_are_explicit() -> None:
    rules = app.ui_component_rules()

    assert rules["action_button"] == "real_streamlit_button"
    assert rules["link_button"] == "real_streamlit_link_button"
    assert rules["static_chip"] == "metadata_only"
    assert rules["disabled_chip"] == "muted_with_reason"
    assert rules["metric_tile"] == "static_by_default"
    assert rules["card"] == "static_unless_action_is_explicit"


def test_ui_semantics_css_prevents_fake_clickable_chips(monkeypatch) -> None:
    rendered: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: rendered.append(str(body)))

    app.inject_styles()

    css = "\n".join(rendered)
    assert ".static-chip:hover" in css
    assert "pointer-events: none" in css
    assert ".ui-action-button" in css
    assert "min-height: 40px" in css
    assert ".metric-tile {" in css
    assert "cursor: default" in css
    assert ".clickable-card:not(.disabled-target-card)" in css


def test_render_action_button_uses_real_streamlit_button(monkeypatch) -> None:
    buttons: list[dict[str, object]] = []

    def fake_button(label: str, **kwargs: object) -> bool:
        buttons.append({"label": label, **kwargs})
        return False

    monkeypatch.setattr(app.st, "button", fake_button)

    app.render_action_button("Открыть", key="open_one", on_click=lambda: None, help_text="target.md")

    assert buttons[0]["label"] == "Открыть"
    assert buttons[0]["key"] == "open_one"
    assert buttons[0]["help"] == "target.md"
    assert buttons[0]["use_container_width"] is True


def test_render_action_button_adds_semantic_button_type(monkeypatch) -> None:
    buttons: list[dict[str, object]] = []

    monkeypatch.setattr(app.st, "button", lambda label, **kwargs: buttons.append({"label": label, **kwargs}) or False)

    app.render_action_button("Открыть", key="semantic_open", on_click=lambda: None)

    assert buttons[0]["type"] == "primary"


def test_render_action_card_requires_enabled_action() -> None:
    with pytest.raises(ValueError, match="enabled action card requires"):
        app.render_action_card("Title", "Body", key_prefix="card")


def test_render_action_card_disables_with_reason(monkeypatch) -> None:
    html_blocks: list[str] = []
    buttons: list[dict[str, object]] = []
    captions: list[str] = []

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app.st, "button", lambda label, **kwargs: buttons.append({"label": label, **kwargs}) or False)
    monkeypatch.setattr(app.st, "caption", lambda value: captions.append(str(value)))

    clicked = app.render_action_card(
        "Missing",
        "Нет target",
        key_prefix="missing_card",
        action_label="Открыть",
        disabled=True,
        disabled_reason="Target не найден",
    )

    assert clicked is False
    assert "disabled-target-card" in html_blocks[0]
    assert buttons[0]["disabled"] is True
    assert captions == ["Target не найден"]


def test_render_warning_state_uses_warning_semantics() -> None:
    rendered = app.render_warning_state("Проверь", "Нужна ручная проверка.", reason="Нет данных")

    assert "ui-state-card" in rendered
    assert "warning-state-card" in rendered
    assert "NEEDS REVIEW" in rendered
    assert "Нет данных" in rendered


def test_render_empty_state_uses_state_card_shell() -> None:
    rendered = app.render_empty_state("Нет данных", "Добавь источник.", action="Открыть настройки")

    assert "ui-state-card" in rendered
    assert "empty-state-card" in rendered
    assert "Открыть настройки" in rendered


def test_render_vault_setup_card_uses_state_card_shell(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: calls.append(str(body)))

    app.render_vault_setup_card("Нет vault", "Укажи путь.", status="ERROR")

    rendered = "\n".join(calls)
    assert "ui-state-card" in rendered
    assert "vault-setup-card" in rendered
    assert "ERROR" in rendered


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


def test_render_internal_action_row_disabled_uses_disabled_chip() -> None:
    target = app.InternalTarget(
        kind="task",
        label="Missing task",
        target_id="missing",
        exists=False,
        disabled_reason="Задача не найдена",
    )

    rendered = app.render_internal_action_row(target, "Missing task", "missing", "TODO")

    assert 'aria-disabled="true"' in rendered
    assert "disabled-chip" in rendered
    assert "Задача не найдена" in rendered
    assert "→ Открыть" not in rendered
    assert "<button" not in rendered


def test_frontmatter_chips_are_static_metadata() -> None:
    rendered = app.render_frontmatter_chips({"tags": ["ml", "pandas"], "level": "beginner"})

    assert rendered.count("static-chip") == 3
    assert "clickable" not in rendered
    assert "<button" not in rendered


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
    monkeypatch.setattr(
        app.st,
        "columns",
        lambda spec, **_kwargs: [FakeColumn() for _ in range(len(spec) if isinstance(spec, list) else spec)],
    )
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
    next_note_href = "?tab=Theory&amp;note=00_Atlas%2FKnowledge%20Map.md"
    assert rendered.index("continue-learning-card") < rendered.index("home-cockpit-grid")
    assert rendered.count(next_note_href) >= 2
    assert "home-cockpit-grid" in rendered
    assert "home-main-column" in rendered
    assert "home-right-rail" in rendered
    assert rendered.index("home-main-column") < rendered.index("home-right-rail")
    assert "home-quality-gate" in rendered
    assert "QUALITY GATE" in rendered
    assert "36<span" in rendered
    assert "clickable-row-list home-action-list" in rendered
    assert "→ Открыть задачу" in rendered
    assert "→ Открыть теорию" in rendered
    assert "Открыть задачу" not in buttons
    assert "Открыть теорию" not in buttons


def test_continue_learning_cta_uses_find_next_note_for_home_and_theory(monkeypatch) -> None:
    note = {
        "section_key": "01_Python",
        "display_name": "Functions.md",
        "relative_path": "01_Python/Functions.md",
        "path": "/vault/01_Python/Functions.md",
        "stem": "Functions",
    }
    sections = {"01_Python": [note]}
    calls: list[dict[str, list[dict[str, str]]]] = []

    def fake_find_next_note(received_sections: dict[str, list[dict[str, str]]]) -> dict[str, str] | None:
        calls.append(received_sections)
        return note

    monkeypatch.setattr(app, "find_next_note", fake_find_next_note)
    home = app.continue_learning_cta_model(sections)
    theory = app.continue_learning_cta_model(sections)

    assert calls == [sections, sections]
    assert home == theory
    assert home["href"] == "?tab=Theory&note=01_Python%2FFunctions.md"
    assert home["title"] == "Продолжить обучение"
    assert home["target_title"] == "01 Python / Functions.md"
    assert home["section"] == "01 Python"
    assert home["status"] == "TODO"


def test_render_continue_learning_cta_is_prominent_clickable_card() -> None:
    rendered = app.render_continue_learning_cta(
        {
            "title": "Продолжить обучение",
            "target_title": "01 Python / Functions.md",
            "section": "01 Python",
            "meta": "Следующая незакрытая заметка.",
            "why": "Продолжи с первого открытого шага.",
            "href": "?tab=Theory&note=01_Python%2FFunctions.md",
            "status": "TODO",
            "exists": True,
        }
    )

    assert 'class="continue-learning-card clickable-row' in rendered
    assert "Продолжить обучение" in rendered
    assert "01 Python / Functions.md" in rendered
    assert "Продолжить обучение →" in rendered
    assert '?tab=Theory&amp;note=01_Python%2FFunctions.md' in rendered


def test_ui_state_persists_onboarding_dismissal(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "user_projects" / "ui_state.json"
    monkeypatch.setattr(app, "UI_STATE_PATH", state_path)
    app.st.session_state.clear()

    assert app.load_ui_state() == {}
    assert app.should_show_onboarding() is True

    app.set_onboarding_dismissed(True)
    app.st.session_state.clear()

    assert app.load_ui_state()["onboarding_dismissed"] is True
    assert app.should_show_onboarding() is False

    app.reopen_onboarding()

    assert app.load_ui_state()["onboarding_dismissed"] is False
    assert app.st.session_state["active_tab"] == "Home"


def test_onboarding_steps_use_existing_learning_targets() -> None:
    note = {
        "section_key": "00_Atlas",
        "display_name": "Knowledge Map.md",
        "relative_path": "00_Atlas/Knowledge Map.md",
        "path": "/vault/00_Atlas/Knowledge Map.md",
        "stem": "Knowledge Map",
    }
    practice = {
        "id": "practice_one",
        "title": "Practice One",
        "section": "Atlas",
        "difficulty": "easy",
        "est_time": "10 мин",
    }
    task = {
        "id": "task_one",
        "title": "Task One",
        "confidence": "high",
        "notebook_label": "Notebook",
    }
    project = runtime_sample_project()

    steps = app.onboarding_steps(
        {"00_Atlas": [note]},
        [practice],
        [task],
        [project],
    )

    assert [step["title"] for step in steps] == [
        "Читай теорию",
        "Закрепи практикой",
        "Реши задачу с авто-проверкой",
        "Собери проект и положи результат в портфолио",
    ]
    assert steps[0]["href"] == "?tab=Theory&note=00_Atlas%2FKnowledge%20Map.md"
    assert "kind=practice" in steps[1]["href"]
    assert "kind=task" in steps[2]["href"]
    assert "kind=milestone" in steps[3]["href"]


def test_render_onboarding_card_has_four_clickable_rows_and_dismiss(monkeypatch) -> None:
    html_blocks: list[str] = []
    buttons: list[dict[str, object]] = []

    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app.st, "button", lambda label, **kwargs: buttons.append({"label": label, **kwargs}) or False)

    app.render_onboarding_card(
        [
            {"title": "Читай теорию", "meta": "next", "href": "?tab=Theory", "action": "Theory", "status": "READY"},
            {"title": "Закрепи практикой", "meta": "card", "href": "?tab=Practice", "action": "Practice", "status": "READY"},
            {"title": "Реши задачу с авто-проверкой", "meta": "task", "href": "?tab=Tasks", "action": "Tasks", "status": "READY"},
            {"title": "Собери проект и положи результат в портфолио", "meta": "project", "href": "?tab=Portfolio", "action": "Portfolio", "status": "READY"},
        ]
    )

    rendered = "\n".join(html_blocks)
    assert "Как учиться в Hub_ML" in rendered
    assert rendered.count('<a class="clickable-row') == 4
    assert "Читай теорию" in rendered
    assert buttons[0]["label"] == "Понятно, скрыть"
    assert buttons[0]["on_click"] is app.dismiss_onboarding


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


def sample_theory_sections() -> dict[str, list[dict[str, str]]]:
    atlas_note = {
        "section_key": "00_Atlas",
        "display_name": "00_Knowledge_Map.md",
        "relative_path": "00_Atlas/00_Knowledge_Map.md",
        "path": "/vault/00_Atlas/00_Knowledge_Map.md",
        "stem": "00_Knowledge_Map",
    }
    python_note = {
        "section_key": "01_Python",
        "display_name": "Python Basics.md",
        "relative_path": "01_Python/Python Basics.md",
        "path": "/vault/01_Python/Python Basics.md",
        "stem": "Python Basics",
    }
    return {"00_Atlas": [atlas_note], "01_Python": [python_note]}


def sample_sequential_theory_sections() -> dict[str, list[dict[str, str]]]:
    def note(section_key: str, display_name: str) -> dict[str, str]:
        return {
            "section_key": section_key,
            "display_name": display_name,
            "relative_path": f"{section_key}/{display_name}",
            "path": f"/vault/{section_key}/{display_name}",
            "stem": Path(display_name).stem,
        }

    return {
        "00_Atlas": [
            note("00_Atlas", "Start.md"),
            note("00_Atlas", "Middle.md"),
            note("00_Atlas", "End.md"),
        ],
        "01_Python": [
            note("01_Python", "Python Basics.md"),
        ],
    }


def test_normalize_theory_note_path_adds_suffix_and_strips_anchor() -> None:
    assert app.normalize_theory_note_path("00 Atlas\\Knowledge Map#section") == "00 Atlas/Knowledge Map.md"
    assert app.normalize_theory_note_path("00_Atlas/00_Knowledge_Map.md") == "00_Atlas/00_Knowledge_Map.md"


def test_find_note_by_path_uses_relative_and_absolute_paths() -> None:
    note, note_index = sample_note_index()

    assert app.find_note_by_path("00_Atlas/00_Knowledge_Map", note_index) is note
    assert app.find_note_by_path("/vault/00_Atlas/00_Knowledge_Map.md", note_index) is note
    assert app.find_note_by_path("missing.md", note_index) is None


def test_theory_section_summary_uses_done_and_total(monkeypatch) -> None:
    sections = sample_theory_sections()
    statuses = {
        "/vault/00_Atlas/00_Knowledge_Map.md": app.STATUS_DONE,
        "/vault/01_Python/Python Basics.md": app.STATUS_READING,
    }

    monkeypatch.setattr(app, "get_note_status", lambda note: statuses[str(note["path"])])

    assert app.theory_section_summary(sections["00_Atlas"] + sections["01_Python"]) == "1/2 done"


def test_theory_section_note_button_state_highlights_current_note(monkeypatch) -> None:
    note = sample_theory_sections()["00_Atlas"][0]

    monkeypatch.setattr(app, "get_note_status", lambda _note: app.STATUS_DONE)

    state = app.theory_section_note_button_state(
        note,
        current_note_path="/vault/00_Atlas/00_Knowledge_Map.md",
        note_index=app.build_note_index({"00_Atlas": [note]}),
    )

    assert state["label"] == "00_Knowledge_Map.md"
    assert state["caption"] == "00_Atlas/00_Knowledge_Map.md"
    assert state["status"] == "PASS"
    assert state["current"] is True
    assert state["disabled"] is False
    assert state["reason"] == ""
    assert state["key"] == "theory_outline_note_00_Atlas_00_Knowledge_Map_md"


def test_theory_section_note_button_state_disables_missing_note() -> None:
    note = {
        "section_key": "00_Atlas",
        "display_name": "Missing.md",
        "relative_path": "00_Atlas/Missing.md",
        "path": "/vault/00_Atlas/Missing.md",
        "stem": "Missing",
    }
    _, note_index = sample_note_index()

    state = app.theory_section_note_button_state(
        note,
        current_note_path="/vault/00_Atlas/00_Knowledge_Map.md",
        note_index=note_index,
    )

    assert state["label"] == "Missing.md"
    assert state["caption"] == "00_Atlas/Missing.md"
    assert state["disabled"] is True
    assert state["reason"] == "Заметка не найдена: 00_Atlas/Missing.md"


def test_render_theory_section_navigator_expands_current_section(monkeypatch) -> None:
    sections = sample_theory_sections()
    current_note = sections["01_Python"][0]
    expanders: list[dict[str, object]] = []
    html_blocks: list[str] = []
    buttons: list[dict[str, object]] = []
    captions: list[str] = []

    def fake_expander(label: str, *, expanded: bool = False):
        expanders.append({"label": label, "expanded": expanded})
        return FakeColumn()

    def fake_button(label: str, **kwargs: object) -> bool:
        buttons.append({"label": label, **kwargs})
        return False

    monkeypatch.setattr(app.st, "expander", fake_expander)
    monkeypatch.setattr(app.st, "button", fake_button)
    monkeypatch.setattr(app.st, "caption", lambda value: captions.append(str(value)))
    monkeypatch.setattr(app, "render_html", lambda markup: html_blocks.append(str(markup)))
    monkeypatch.setattr(app, "get_note_status", lambda note: app.STATUS_DONE if note is current_note else app.STATUS_READING)

    app.render_theory_section_navigator(sections, current_note)

    assert [item["expanded"] for item in expanders] == [False, True]
    assert "00 Atlas · 0/1 done" in str(expanders[0]["label"])
    assert "01 Python · 1/1 done" in str(expanders[1]["label"])
    rendered = "\n".join(html_blocks)
    assert "theory-section-navigator" in rendered
    assert "theory-outline-current" in rendered
    assert "Python Basics.md" in rendered
    assert [button["label"] for button in buttons] == ["00_Knowledge_Map.md", "Python Basics.md"]
    assert all(button["on_click"] is app.open_theory_note for button in buttons)
    assert buttons[1]["args"] == ("01_Python/Python Basics.md", app.build_note_index(sections), False)
    assert captions == ["00_Atlas/00_Knowledge_Map.md", "01_Python/Python Basics.md"]


def test_theory_note_position_indicator_uses_position_within_section() -> None:
    sections = sample_sequential_theory_sections()
    note = sections["00_Atlas"][1]

    assert app.theory_note_position_text(sections, note) == "00 Atlas · заметка 2 из 3"


def test_render_note_header_includes_position_indicator(monkeypatch) -> None:
    sections = sample_sequential_theory_sections()
    note = sections["00_Atlas"][1]
    rendered: list[str] = []

    monkeypatch.setattr(app.st, "markdown", lambda body, **_kwargs: rendered.append(str(body)))
    monkeypatch.setattr(app, "get_note_status", lambda _note: app.STATUS_READING)

    app.render_note_header(
        "00_Atlas",
        note,
        {},
        position_text=app.theory_note_position_text(sections, note),
    )

    assert "theory-position-chip" in rendered[0]
    assert "00 Atlas · заметка 2 из 3" in rendered[0]


def test_theory_adjacent_note_targets_use_same_section_order() -> None:
    sections = sample_sequential_theory_sections()
    note = sections["00_Atlas"][1]

    previous_target, next_target = app.theory_adjacent_note_targets(sections, note)

    assert previous_target is not None
    assert previous_target["note"]["display_name"] == "Start.md"
    assert previous_target["context"] == "Предыдущая заметка"
    assert next_target is not None
    assert next_target["note"]["display_name"] == "End.md"
    assert next_target["context"] == "Следующая заметка"


def test_theory_adjacent_note_targets_cross_section_boundary() -> None:
    sections = sample_sequential_theory_sections()
    note = sections["00_Atlas"][2]

    previous_target, next_target = app.theory_adjacent_note_targets(sections, note)

    assert previous_target is not None
    assert previous_target["note"]["display_name"] == "Middle.md"
    assert next_target is not None
    assert next_target["note"]["display_name"] == "Python Basics.md"
    assert next_target["context"] == "Следующий раздел: 01 Python"


def test_theory_adjacent_note_targets_omit_missing_edges() -> None:
    sections = sample_sequential_theory_sections()

    first_previous, first_next = app.theory_adjacent_note_targets(sections, sections["00_Atlas"][0])
    last_previous, last_next = app.theory_adjacent_note_targets(sections, sections["01_Python"][0])

    assert first_previous is None
    assert first_next is not None
    assert last_previous is not None
    assert last_next is None


def test_render_theory_prev_next_strip_renders_only_available_targets() -> None:
    sections = sample_sequential_theory_sections()
    rendered = app.render_theory_prev_next_strip(sections, sections["00_Atlas"][2])

    assert "theory-prev-next-strip" in rendered
    assert "← Middle.md" in rendered
    assert "Python Basics.md →" in rendered
    assert "Следующий раздел: 01 Python" in rendered
    assert "disabled-target-card" not in rendered
    assert "<button" not in rendered
    assert rendered.count('<a class="clickable-row') == 2


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


def test_open_theory_note_ignores_missing_target_without_history(monkeypatch) -> None:
    _, note_index = sample_note_index()
    reruns: list[bool] = []
    app.st.session_state.clear()
    app.st.session_state["active_note_path"] = "/vault/Home.md"

    monkeypatch.setattr(app.st, "rerun", lambda: reruns.append(True))

    app.open_theory_note("missing target", note_index)

    assert app.st.session_state["active_note_path"] == "/vault/Home.md"
    assert app.st.session_state.get("note_history") is None
    assert reruns == []


def test_open_theory_note_accepts_label_path_mismatch(monkeypatch) -> None:
    note, note_index = sample_note_index()
    reruns: list[bool] = []
    app.st.session_state.clear()

    monkeypatch.setattr(app.st, "rerun", lambda: reruns.append(True))

    app.open_theory_note("00 Atlas / Knowledge Map", note_index)

    assert app.st.session_state["active_note_path"] == note["path"]
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
    assert buttons[0]["args"] == ("00_Atlas/00_Knowledge_Map.md", note_index, False)
    assert buttons[0]["disabled"] is False
    assert captions == ["00_Atlas/00_Knowledge_Map.md"]


def test_render_note_link_button_callback_opens_resolved_outgoing_path(monkeypatch) -> None:
    note, note_index = sample_note_index()
    buttons: list[dict[str, object]] = []
    opened: list[tuple[str, dict[str, object], bool]] = []

    monkeypatch.setattr(app.st, "button", lambda label, **kwargs: buttons.append({"label": label, **kwargs}) or False)
    monkeypatch.setattr(app.st, "caption", lambda _value: None)
    monkeypatch.setattr(
        app,
        "open_theory_note",
        lambda path, index, rerun=True: opened.append((str(path), index, bool(rerun))),
    )

    app.render_link_card({"label": "Human label", "resolved_note": note, "status": "resolved"}, 0, "outgoing", note_index)
    buttons[0]["on_click"](*buttons[0]["args"])

    assert buttons[0]["label"] == "🔗 Human label"
    assert opened == [("00_Atlas/00_Knowledge_Map.md", note_index, False)]


def test_render_link_card_backlink_callback_opens_source_note(monkeypatch) -> None:
    note, note_index = sample_note_index()
    buttons: list[dict[str, object]] = []
    opened: list[tuple[str, dict[str, object], bool]] = []

    monkeypatch.setattr(app.st, "button", lambda label, **kwargs: buttons.append({"label": label, **kwargs}) or False)
    monkeypatch.setattr(app.st, "caption", lambda _value: None)
    monkeypatch.setattr(
        app,
        "open_theory_note",
        lambda path, index, rerun=True: opened.append((str(path), index, bool(rerun))),
    )

    app.render_link_card({"label": "Backlink title", "resolved_note": note, "status": "resolved"}, 1, "backlink", note_index)
    buttons[0]["on_click"](*buttons[0]["args"])

    assert buttons[0]["label"] == "🔗 Backlink title"
    assert opened == [("00_Atlas/00_Knowledge_Map.md", note_index, False)]


def test_open_theory_note_path_callback_does_not_request_rerun(monkeypatch) -> None:
    opened: list[tuple[str, dict[str, object], bool]] = []

    def fake_open_theory_note(relative_path: str, note_index: dict[str, object], rerun: bool = True) -> None:
        opened.append((relative_path, note_index, rerun))

    monkeypatch.setattr(app, "build_note_index", lambda sections: {"built": sections})
    monkeypatch.setattr(app, "open_theory_note", fake_open_theory_note)

    app.open_theory_note_path("00_Atlas/00_Knowledge_Map.md", {"00_Atlas": []})

    assert opened == [("00_Atlas/00_Knowledge_Map.md", {"built": {"00_Atlas": []}}, False)]


def test_render_note_target_button_missing_target_is_disabled(monkeypatch) -> None:
    _, note_index = sample_note_index()
    buttons: list[dict[str, object]] = []
    captions: list[str] = []

    def fake_button(label: str, **kwargs: object) -> None:
        buttons.append({"label": label, **kwargs})

    monkeypatch.setattr(app.st, "button", fake_button)
    monkeypatch.setattr(app.st, "caption", lambda value: captions.append(str(value)))

    rendered = app.render_note_target_button("Missing long display label that should not be the path", "missing_note", note_index, "outgoing")

    assert rendered is False
    assert len(buttons) == 1
    assert buttons[0]["label"] == "Missing long display label that should not be the path"
    assert buttons[0]["disabled"] is True
    assert buttons[0]["on_click"] is None
    assert "Target не найден" in str(buttons[0]["help"])
    assert captions == ["missing_note.md · target не найден"]


def test_render_note_target_button_key_is_stable(monkeypatch) -> None:
    _, note_index = sample_note_index()
    buttons: list[dict[str, object]] = []

    def fake_button(label: str, **kwargs: object) -> None:
        buttons.append({"label": label, **kwargs})

    monkeypatch.setattr(app.st, "button", fake_button)
    monkeypatch.setattr(app.st, "caption", lambda _value: None)

    app.render_note_target_button("Knowledge Map", "00_Atlas/00_Knowledge_Map.md", note_index, "outgoing")
    app.render_note_target_button("Knowledge Map", "00_Atlas/00_Knowledge_Map.md", note_index, "outgoing")

    assert buttons[0]["key"] == buttons[1]["key"]
    assert buttons[0]["key"] == "outgoing_00_Atlas_00_Knowledge_Map_md_Knowledge_Map"


def test_render_theory_note_body_uses_page_specific_wrapper() -> None:
    rendered = app.render_theory_note_body("# Title\n\nSee [[A & B]].")

    assert rendered.startswith('<article class="theory-note-body">')
    assert "obsidian-link-static static-chip" in rendered
    assert "A &amp; B" in rendered
    assert "stMarkdownContainer" not in rendered


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


def test_render_link_card_missing_target_disables_button_with_reason(monkeypatch) -> None:
    _, note_index = sample_note_index()
    buttons: list[dict[str, object]] = []
    captions: list[str] = []

    def fake_button(label: str, **kwargs: object) -> None:
        buttons.append({"label": label, **kwargs})

    monkeypatch.setattr(app.st, "button", fake_button)
    monkeypatch.setattr(app.st, "caption", lambda value: captions.append(str(value)))

    app.render_link_card({"label": "Missing note", "target": "No Folder/Missing"}, 0, "outgoing_missing", note_index)

    assert len(buttons) == 1
    assert buttons[0]["label"] == "Missing note"
    assert buttons[0]["disabled"] is True
    assert "Target не найден" in str(buttons[0]["help"])
    assert captions == ["No Folder/Missing.md · target не найден"]


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


def test_open_internal_target_fields_can_suppress_callback_rerun(monkeypatch) -> None:
    opened: list[tuple[app.InternalTarget, bool]] = []

    monkeypatch.setattr(app, "open_internal_target", lambda target, rerun=True: opened.append((target, rerun)))

    app.open_internal_target_fields(
        "project",
        "Orders",
        "orders_eda",
        "",
        "orders_eda",
        "",
        "data_lab",
        True,
        "",
        rerun=False,
    )

    target, rerun = opened[0]
    assert target.kind == "project"
    assert target.target_id == "orders_eda"
    assert rerun is False


def test_dataset_internal_target_selects_dataset(monkeypatch) -> None:
    reruns: list[bool] = []
    app.st.session_state.clear()
    monkeypatch.setattr(app.st, "rerun", lambda: reruns.append(True))

    app.open_internal_target(app.InternalTarget(kind="dataset", label="Dataset", target_id="df_orders.csv"))

    assert app.st.session_state["active_tab"] == "📊 Datasets"
    assert app.st.session_state["selected_dataset"] == "df_orders.csv"
    assert reruns == [True]


def test_semantic_search_index_state_handles_empty_ready_and_failed() -> None:
    empty = app.semantic_search_index_state(None, {})
    ready = app.semantic_search_index_state(app.SearchIndex(items=[]), {"items": 0})
    failed = app.semantic_search_index_state(None, {"status": "failed", "error": "boom"})

    assert empty["status"] == "not_built"
    assert empty["chip"] == "TODO"
    assert "Обновить индекс поиска" in empty["message"]
    assert ready["status"] == "ready"
    assert ready["chip"] == "READY"
    assert failed["status"] == "failed"
    assert failed["chip"] == "ERROR"
    assert "boom" in failed["message"]


def test_semantic_search_note_result_target_validates_path() -> None:
    note = sample_theory_sections()["00_Atlas"][0]
    sections = {"00_Atlas": [note]}
    result = SimpleNamespace(
        source="theory_note",
        id="note:00_Atlas/00_Knowledge_Map.md",
        title="Human title",
        score=0.91,
        path="00_Atlas/00_Knowledge_Map.md",
        payload={},
    )

    target = app.semantic_search_result_target(result, sections, [], [])

    assert target.kind == "theory_note"
    assert target.label == "Human title"
    assert target.path == "00_Atlas/00_Knowledge_Map.md"
    assert target.target_id == "00_Atlas/00_Knowledge_Map.md"
    assert target.exists is True


def test_semantic_search_missing_note_result_is_disabled() -> None:
    result = SimpleNamespace(
        source="theory_note",
        id="note:missing.md",
        title="Missing note",
        score=0.4,
        path="missing.md",
        payload={},
    )

    target = app.semantic_search_result_target(result, {}, [], [])

    assert target.kind == "theory_note"
    assert target.exists is False
    assert "not found" in target.disabled_reason


def test_semantic_search_practice_and_task_targets_validate_ids() -> None:
    practice_result = SimpleNamespace(
        source="practice",
        id="practice:orders_practice",
        title="Orders practice",
        score=0.7,
        path="",
        payload={"card_id": "orders_practice"},
    )
    task_result = SimpleNamespace(
        source="task",
        id="task:python_basics_records",
        title="Python task",
        score=0.6,
        path="python_basics_records",
        payload={"task_id": "python_basics_records"},
    )

    practice = app.semantic_search_result_target(
        practice_result,
        {},
        [{"id": "orders_practice", "title": "Orders practice"}],
        [],
    )
    task = app.semantic_search_result_target(
        task_result,
        {},
        [],
        [{"id": "python_basics_records", "title": "Python task"}],
    )
    missing_task = app.semantic_search_result_target(task_result, {}, [], [])

    assert practice.kind == "practice"
    assert practice.exists is True
    assert practice.target_id == "orders_practice"
    assert task.kind == "task"
    assert task.exists is True
    assert task.target_id == "python_basics_records"
    assert missing_task.exists is False
    assert "not found" in missing_task.disabled_reason


def test_render_semantic_search_result_action_opens_note_target(monkeypatch) -> None:
    result = SimpleNamespace(
        source="theory_note",
        id="note:00_Atlas/00_Knowledge_Map.md",
        title="Knowledge Map",
        score=0.91,
        path="00_Atlas/00_Knowledge_Map.md",
        payload={},
    )
    target = app.InternalTarget(
        kind="theory_note",
        label="Knowledge Map",
        target_id="00_Atlas/00_Knowledge_Map.md",
        path="00_Atlas/00_Knowledge_Map.md",
    )
    buttons: list[dict[str, object]] = []

    monkeypatch.setattr(app.st, "button", lambda label, **kwargs: buttons.append({"label": label, **kwargs}) or False)

    app.render_semantic_search_result_action(result, target, key_prefix="semantic_search", index=0)

    assert buttons[0]["label"] == "Открыть заметку"
    assert buttons[0]["disabled"] is False
    assert buttons[0]["on_click"] is app.open_internal_target_fields
    assert buttons[0]["args"] == (
        "theory_note",
        "Knowledge Map",
        "00_Atlas/00_Knowledge_Map.md",
        "00_Atlas/00_Knowledge_Map.md",
        "",
        "",
        "",
        True,
        "",
        False,
    )


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
