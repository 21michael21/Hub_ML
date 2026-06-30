from __future__ import annotations

import re

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import Page, expect


RUNTIME_MARKERS = (
    "Traceback",
    "TypeError",
    "KeyError",
    "ImportError",
    "safe_widget_key",
    "takes 2 positional arguments",
)
RAW_HTML_MARKERS = ("<div", "</div>", 'class="', "section-eyebrow")


def visible_text(page: Page) -> str:
    return page.locator("body").inner_text(timeout=10_000)


def assert_clean_page(page: Page) -> None:
    text = visible_text(page)
    for marker in (*RUNTIME_MARKERS, *RAW_HTML_MARKERS):
        assert marker not in text


def open_app(page: Page, app_url: str, *, width: int = 1440, height: int = 900) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(app_url, wait_until="domcontentloaded", timeout=20_000)
    expect(page.locator("body")).to_contain_text("Hub_ML", timeout=30_000)
    expect(page.locator("body")).to_contain_text("Открыть теорию", timeout=30_000)
    assert_clean_page(page)


def click_button_containing(page: Page, text: str, *, timeout_ms: int = 8_000) -> bool:
    def attempt_click() -> dict[str, object]:
        return page.evaluate(
            """({ text }) => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const target = buttons.find((button) => (button.innerText || button.textContent || '').includes(text));
                if (!target) {
                    return { clicked: false, labels: buttons.map((button) => (button.innerText || button.textContent || '').trim()).slice(0, 60) };
                }
                target.scrollIntoView({ block: 'center', inline: 'nearest' });
                target.click();
                return { clicked: true, labels: [] };
            }""",
            {"text": text},
        )

    result = attempt_click()
    if not result["clicked"] and any("keyboard_double_arrow_right" in str(label) for label in result["labels"]):
        page.evaluate(
            """() => {
                const toggler = Array.from(document.querySelectorAll('button'))
                    .find((button) => (button.innerText || button.textContent || '')
                        .includes('keyboard_double_arrow_right'));
                if (toggler) toggler.click();
            }"""
        )
        page.wait_for_timeout(600)
        result = attempt_click()
    if not result["clicked"]:
        return False
    page.wait_for_timeout(min(timeout_ms, 1_000))
    assert_clean_page(page)
    return True

def click_first_available_button(page: Page, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        if click_button_containing(page, label):
            return label
    return None


def click_nav(page: Page, label: str) -> None:
    active_markers = {
        "Home": ("Hub_ML", "Открыть теорию"),
        "Theory": ("Theory note", "Find related"),
        "Practice": ("Practice", "Practice cards"),
        "Tasks": ("Tasks", "Автозадач"),
        "Datasets": ("CSV-файлы из папки", "Datasets"),
        "Notebook": ("Notebook", "Jupyter"),
        "Data Lab": ("Data Lab Projects", "Каталог проектов", "Шаги проекта"),
        "ML Lab": ("ML Lab", "Classic ML", "Experiment Tracker Lite"),
        "Portfolio": ("Portfolio Export", "Markdown exporter"),
        "Experiments": ("Experiments", "Experiment runs"),
        "Algorithms": ("Algorithms", "Interview Arena"),
        "Interviews": ("Interviews", "Вопросов"),
        "Theory Quality": ("Theory Quality", "Content Gate"),
        "Links Health": ("Links Health", "Obsidian links"),
    }
    if body_has_any(page, active_markers.get(label, (label,))):
        assert_clean_page(page)
        return
    nav_aliases = {
        "Practice": ("Practice", "✎ Practice", "✎"),
        "Tasks": ("Tasks", "✓ Tasks", "✓"),
        "Datasets": ("Datasets", "▨ Datasets", "▨"),
        "Notebook": ("Notebook", "▦ Notebook", "▦"),
        "Data Lab": ("Data Lab", "▣ Data Lab", "▣"),
        "ML Lab": ("ML Lab", "▧ ML Lab", "▧"),
        "Portfolio": ("Portfolio", "□ Portfolio", "□"),
        "Experiments": ("Experiments", "◌ Experiments", "◌"),
        "Algorithms": ("Algorithms", "⌘ Algorithms", "⌘"),
        "Interviews": ("Interviews", "? Interviews", "?"),
        "Theory Quality": ("Theory Quality", "◇ Theory Quality", "◇"),
        "Links Health": ("Links Health", "↔ Links Health", "↔"),
    }
    clicked = click_first_available_button(page, nav_aliases.get(label, (label,)))
    assert clicked is not None, f"Navigation item not found: {label}"
    expect(page.locator("body")).to_contain_text(active_markers.get(label, (label,))[0], timeout=10_000)
    assert_clean_page(page)


def fill_input_by_label(page: Page, label: str, value: str) -> bool:
    locator = page.get_by_label(label, exact=True)
    try:
        if locator.count() == 0:
            return False
        locator.fill(value, timeout=5_000)
        return True
    except Exception:
        return False


def body_has_any(page: Page, patterns: tuple[str, ...]) -> bool:
    text = visible_text(page)
    return any(pattern in text for pattern in patterns)


def test_home_actions_are_clickable(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)

    right_rail_gate = page.locator(".home-right-rail .home-quality-gate")
    expect(right_rail_gate).to_have_count(1, timeout=10_000)
    expect(right_rail_gate).to_contain_text("QUALITY GATE", timeout=10_000)

    if click_button_containing(page, "Открыть теорию"):
        expect(page.locator("body")).to_contain_text("Theory", timeout=10_000)
        assert body_has_any(page, ("Theory note", ".md", "Knowledge Map", "Welcome"))

    open_app(page, streamlit_app_url)
    if click_button_containing(page, "Открыть проект"):
        assert body_has_any(page, ("Project", "milestone", "Milestone", "Data Lab", "ML Lab"))

    open_app(page, streamlit_app_url)
    if click_button_containing(page, "Открыть задачу"):
        assert body_has_any(page, ("Tasks", "Условие", "Решение", "Assert-проверки"))


def test_core_pages_do_not_show_raw_html_or_runtime_errors(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)

    for label in (
        "Home",
        "Theory",
        "Practice",
        "Tasks",
        "Datasets",
        "Notebook",
        "Data Lab",
        "ML Lab",
        "Portfolio",
        "Experiments",
        "Algorithms",
        "Interviews",
        "Theory Quality",
        "Links Health",
    ):
        click_nav(page, label)
        assert_clean_page(page)


def test_data_lab_project_workflow_clickability(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Data Lab")

    opened = click_first_available_button(page, ("Выбрать проект", "Открыть следующий шаг", "Открыть проект"))
    assert opened is not None or body_has_any(page, ("Следующий шаг", "Шаги проекта", "Каталог проектов"))
    assert_clean_page(page)

    clicked_milestone = click_first_available_button(
        page,
        ("Открыть следующий шаг", "Отметить готово", "Сбросить milestone", "▶ Run milestone"),
    )
    if clicked_milestone is None:
        click_button_containing(page, "Define")
    assert_clean_page(page)
    assert "widget-key" not in visible_text(page)


def test_classic_ml_experiment_tracker_manual_save(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "ML Lab")

    click_first_available_button(page, ("Выбрать проект", "Открыть следующий шаг", "Открыть проект"))
    expect(page.locator("body")).to_contain_text("Experiment Tracker Lite", timeout=10_000)

    if click_button_containing(page, "Save current experiment summary"):
        fill_input_by_label(page, "Model name", "E2E baseline")
        fill_input_by_label(page, "accuracy", "0.5")
        fill_input_by_label(page, "Notes", "E2E smoke")
        saved = click_button_containing(page, "Save experiment record")
        assert saved
        expect(page.locator("body")).to_contain_text("E2E baseline", timeout=15_000)
        assert "df_orders.csv," not in visible_text(page)

    assert_clean_page(page)


def test_portfolio_exporter_preview_smoke(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Portfolio")

    assert body_has_any(page, ("Portfolio Export", "Markdown exporter", "Экспорт пока недоступен"))
    if click_button_containing(page, "Markdown preview"):
        assert body_has_any(page, ("# Portfolio", "## Projects", "## Practice", "Limitations", "Next steps"))
    assert_clean_page(page)


def test_interview_arena_modes_and_minimal_answer(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Interviews")

    for mode in ("Learn", "Practice", "Timed Mock", "Review"):
        click_button_containing(page, mode)
        assert_clean_page(page)

    click_button_containing(page, "Practice")
    fill_input_by_label(page, "Answer notes", "E2E smoke answer")
    click_button_containing(page, "Save answer")
    assert_clean_page(page)
    assert body_has_any(page, ("Interview", "attempt", "Вопросы", "Ответь"))


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)])
def test_responsive_home_and_projects_have_no_horizontal_overflow(
    page: Page,
    streamlit_app_url: str,
    viewport: tuple[int, int],
) -> None:
    width, height = viewport
    open_app(page, streamlit_app_url, width=width, height=height)
    expect(page.locator(".home-cockpit-grid")).to_have_count(1, timeout=10_000)
    expect(page.locator(".home-right-rail .home-quality-gate")).to_have_count(1, timeout=10_000)
    assert_clean_page(page)
    overflow = page.evaluate(
        """() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth"""
    )
    assert overflow <= 24

    click_nav(page, "Data Lab")
    assert_clean_page(page)
    overflow = page.evaluate(
        """() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth"""
    )
    assert overflow <= 24
