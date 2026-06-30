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


def visible_prose_text(page: Page) -> str:
    return str(
        page.evaluate(
            """() => {
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll('style, script, pre, code').forEach((node) => node.remove());
                return clone.innerText || clone.textContent || '';
            }"""
        )
    )


def assert_clean_page(page: Page) -> None:
    text = visible_prose_text(page)
    for marker in (*RUNTIME_MARKERS, *RAW_HTML_MARKERS):
        assert marker not in text


def open_app(page: Page, app_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(app_url, wait_until="domcontentloaded", timeout=20_000)
    expect(page.locator("body")).to_contain_text("Hub_ML", timeout=30_000)
    expect(page.locator("body")).to_contain_text("Открыть теорию", timeout=30_000)
    assert_clean_page(page)


def click_visible_button_containing(page: Page, text: str, *, wait_ms: int = 900) -> str | None:
    result = page.evaluate(
        """({ text }) => {
            const controls = Array.from(document.querySelectorAll('button, a[href]'));
            const target = controls.find((control) => {
                const label = (control.innerText || control.textContent || '').trim();
                const rect = control.getBoundingClientRect();
                return label.includes(text) && rect.width > 0 && rect.height > 0 && !control.disabled;
            });
            if (!target) {
                return null;
            }
            target.scrollIntoView({ block: 'center', inline: 'nearest' });
            target.click();
            return (target.innerText || target.textContent || '').trim();
        }""",
        {"text": text},
    )
    if result is None:
        return None
    page.wait_for_timeout(wait_ms)
    assert_clean_page(page)
    return str(result)


def click_visible_graph_link(page: Page, *, require_path_label: bool = False, wait_ms: int = 900) -> str | None:
    result = page.evaluate(
        """({ requirePathLabel }) => {
            const visibleRect = (element) => {
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 ? rect : null;
            };
            const buttons = Array.from(document.querySelectorAll('button'));
            const randomButton = buttons.find((button) => {
                const rect = visibleRect(button);
                const label = (button.innerText || button.textContent || '').trim();
                return rect && label.includes('Открыть случайную непройденную заметку');
            });
            if (!randomButton) {
                return null;
            }
            const graphStartY = randomButton.getBoundingClientRect().top + window.scrollY;
            const target = buttons.find((button) => {
                const rect = visibleRect(button);
                const label = (button.innerText || button.textContent || '').trim();
                const y = rect ? rect.top + window.scrollY : 0;
                return (
                    rect &&
                    y > graphStartY &&
                    label.includes('🔗') &&
                    (!requirePathLabel || label.includes(' / ')) &&
                    !button.disabled
                );
            });
            if (!target) {
                return null;
            }
            target.scrollIntoView({ block: 'center', inline: 'nearest' });
            target.click();
            return (target.innerText || target.textContent || '').trim();
        }""",
        {"requirePathLabel": require_path_label},
    )
    if result is None:
        return None
    page.wait_for_timeout(wait_ms)
    assert_clean_page(page)
    return str(result)


def click_nav(page: Page, label: str) -> None:
    nav_aliases = {
        "Data Lab": ("Data Lab", "▣ Data Lab", "▣"),
        "ML Lab": ("ML Lab", "▧ ML Lab", "▧"),
        "Portfolio": ("Portfolio", "□ Portfolio", "□"),
        "Algorithms": ("Algorithms", "⌘ Algorithms", "⌘"),
        "Interviews": ("Interviews", "? Interviews", "?"),
        "Experiments": ("Experiments", "◌ Experiments", "◌"),
    }
    clicked = None
    for candidate in nav_aliases.get(label, (label,)):
        clicked = click_visible_button_containing(page, candidate)
        if clicked is not None:
            break
    if clicked is None:
        page.evaluate(
            """() => {
                const toggler = Array.from(document.querySelectorAll('button'))
                    .find((button) => (button.innerText || button.textContent || '')
                        .includes('keyboard_double_arrow_right'));
                if (toggler) toggler.click();
            }"""
        )
        page.wait_for_timeout(600)
        for candidate in nav_aliases.get(label, (label,)):
            clicked = click_visible_button_containing(page, candidate)
            if clicked is not None:
                break
    assert clicked is not None, f"Navigation button not found: {label}"


def body_has_any(page: Page, patterns: tuple[str, ...]) -> bool:
    text = visible_text(page)
    return any(pattern in text for pattern in patterns)


def click_first_available_button(page: Page, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        clicked = click_visible_button_containing(page, label)
        if clicked is not None:
            return clicked
    return None


def click_first_visible_checkbox_containing(page: Page, labels: tuple[str, ...]) -> str | None:
    result = page.evaluate(
        """({ labels }) => {
            const labelNodes = Array.from(document.querySelectorAll('label'));
            for (const wanted of labels) {
                const label = labelNodes.find((node) => {
                    const text = (node.innerText || node.textContent || '').trim();
                    const rect = node.getBoundingClientRect();
                    return text.includes(wanted) && rect.width > 0 && rect.height > 0;
                });
                if (!label) continue;
                const input = label.querySelector('input[type="checkbox"]')
                    || document.getElementById(label.getAttribute('for') || '');
                if (input && input.disabled) continue;
                label.scrollIntoView({ block: 'center', inline: 'nearest' });
                label.click();
                return (label.innerText || label.textContent || '').trim();
            }
            return null;
        }""",
        {"labels": list(labels)},
    )
    if result is None:
        return None
    page.wait_for_timeout(600)
    assert_clean_page(page)
    return str(result)


def fill_input_by_label(page: Page, label: str, value: str) -> bool:
    locator = page.get_by_label(label, exact=True)
    try:
        if locator.count() == 0:
            return False
        locator.fill(value, timeout=5_000)
        return True
    except Exception:
        return False


def assert_no_horizontal_overflow(page: Page, max_extra_px: int = 24) -> None:
    overflow = page.evaluate(
        """() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth"""
    )
    assert overflow <= max_extra_px


def open_theory_from_home(page: Page, app_url: str) -> str:
    open_app(page, app_url)
    before = visible_text(page)
    clicked = click_visible_button_containing(page, "Открыть теорию")
    assert clicked is not None
    expect(page.locator("body")).to_contain_text("Theory", timeout=10_000)
    expect(page.locator("body")).to_contain_text("Исходящие ссылки", timeout=10_000)
    after = visible_text(page)
    assert after != before
    assert_clean_page(page)
    return after


def test_theory_outgoing_link_click_opens_target(page: Page, streamlit_app_url: str) -> None:
    before = open_theory_from_home(page, streamlit_app_url)

    clicked = click_visible_graph_link(page)
    assert clicked is not None, "Expected at least one resolved outgoing Theory link button"
    assert clicked.startswith("🔗")

    after = visible_text(page)
    assert after != before
    assert "Theory" in after
    assert_clean_page(page)


def test_theory_backlink_click_opens_source_note(page: Page, streamlit_app_url: str) -> None:
    open_theory_from_home(page, streamlit_app_url)

    outgoing_clicked = click_visible_graph_link(page)
    assert outgoing_clicked is not None, "Need an outgoing link target with backlinks"
    assert outgoing_clicked.startswith("🔗")
    expect(page.locator("body")).to_contain_text("Открыть случайную непройденную заметку", timeout=10_000)
    before = visible_text(page)

    backlink_clicked = click_visible_graph_link(page, require_path_label=True)
    assert backlink_clicked is not None, "Expected a backlink button on the target note"
    assert backlink_clicked.startswith("🔗")
    after = visible_text(page)

    assert after != before
    assert "Theory" in after
    assert_clean_page(page)


def test_theory_outline_section_note_button_opens_note(page: Page, streamlit_app_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(f"{streamlit_app_url}?tab=Theory&note=welcome.md", wait_until="domcontentloaded", timeout=20_000)
    expect(page.locator("body")).to_contain_text("Разделы Theory", timeout=30_000)

    click_visible_button_containing(page, "00 Atlas")
    before = visible_text(page)
    clicked = click_visible_button_containing(page, "00_Knowledge_Map.md")
    assert clicked is not None, "Expected real note button inside Theory section outline"

    expect(page.locator("body")).to_contain_text("00_Atlas/00_Knowledge_Map.md", timeout=10_000)
    after = visible_text(page)
    assert after != before
    assert "Knowledge Map" in after or "00_Knowledge_Map.md" in after
    assert_clean_page(page)


def test_random_uncompleted_note_button_is_safe(page: Page, streamlit_app_url: str) -> None:
    before = open_theory_from_home(page, streamlit_app_url)

    clicked = click_visible_button_containing(page, "Открыть случайную непройденную заметку")
    assert clicked is not None
    after = visible_text(page)

    assert after != "" and ("Theory" in after or "Заметки" in after)
    assert after != before or "непройденную заметку" in after
    assert_clean_page(page)


def test_home_next_theory_action_opens_theory(page: Page, streamlit_app_url: str) -> None:
    open_theory_from_home(page, streamlit_app_url)

    text = visible_text(page)
    assert re.search(r"Theory|Исходящие ссылки|Обратные ссылки|\\.md", text)
    assert_clean_page(page)


def test_home_next_task_action_opens_task_detail(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)

    clicked = click_visible_button_containing(page, "Открыть задачу")
    if clicked is None:
        assert "Задачи ментора закрыты" in visible_text(page)
        assert_clean_page(page)
        return

    text = visible_text(page)
    assert "Tasks" in text or "Автозадач" in text
    assert any(marker in text for marker in ("Условие", "Решение", "Assert-проверки", "Notebook"))
    assert_clean_page(page)


def test_home_next_project_milestone_opens_project_detail(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)

    clicked = click_visible_button_containing(page, "Открыть проект")
    if clicked is None:
        assert "Проекты закрыты" in visible_text(page)
        assert_clean_page(page)
        return

    text = visible_text(page)
    assert any(marker in text for marker in ("Следующий шаг", "Шаги проекта", "milestone", "Experiment Tracker Lite"))
    assert_clean_page(page)


def test_data_lab_project_next_milestone_flow(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Data Lab")
    expect(page.locator("body")).to_contain_text("Каталог проектов", timeout=10_000)

    click_first_available_button(page, ("Выбрать проект", "Выбран"))
    expect(page.locator("body")).to_contain_text("Перед стартом", timeout=10_000)
    expect(page.locator("body")).to_contain_text("Шаги проекта", timeout=10_000)

    opened = click_first_available_button(page, ("Открыть следующий шаг", "Отметить готово", "Сбросить milestone"))
    assert opened is not None or body_has_any(page, ("Проект готов", "Шаг 1:", "Run milestone"))

    checklist_clicked = click_first_visible_checkbox_containing(page, ("Loaded data", "Summary written"))
    if checklist_clicked is None:
        checklist_clicked = click_first_available_button(page, ("Отметить готово",))
    assert checklist_clicked is not None or body_has_any(page, ("Checklist", "Portfolio output", "Writing prompt", "Solution code"))
    assert_clean_page(page)


def test_ml_lab_project_detail_and_milestone_flow(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "ML Lab")

    expect(page.locator("body")).to_contain_text("ML Lab", timeout=10_000)
    expect(page.locator("body")).to_contain_text("Перед стартом", timeout=10_000)
    expect(page.locator("body")).to_contain_text("Шаги проекта", timeout=10_000)
    assert body_has_any(page, ("Следующий шаг", "Проект готов", "Experiment Tracker Lite"))

    opened = click_first_available_button(page, ("Открыть следующий шаг", "Отметить готово", "▶ Run milestone"))
    assert opened is not None or body_has_any(page, ("Шаг 1:", "Solution code", "Writing prompt"))
    assert_clean_page(page)


def test_experiment_tracker_form_or_empty_state_renders(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "ML Lab")

    expect(page.locator("body")).to_contain_text("Experiment Tracker Lite", timeout=10_000)
    text = visible_text(page)
    assert body_has_any(page, ("Experiment records пока нет", "Save current experiment summary", "Runs"))

    if click_visible_button_containing(page, "Save current experiment summary") is not None:
        fill_input_by_label(page, "Model name", "E2E baseline")
        fill_input_by_label(page, "accuracy", "0.5")
        fill_input_by_label(page, "Notes", "E2E smoke")
        assert "Model name" in visible_text(page) or "E2E baseline" in visible_text(page)
    else:
        assert "Experiment records пока нет" in text or "Runs" in text
    assert_clean_page(page)


def test_portfolio_preview_or_empty_state_is_clickable_safe(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Portfolio")

    expect(page.locator("body")).to_contain_text("Portfolio", timeout=10_000)
    if click_visible_button_containing(page, "Markdown preview") is not None:
        assert body_has_any(page, ("# Portfolio", "## Projects", "## Practice", "Markdown preview"))
    else:
        assert body_has_any(page, ("Экспорт пока недоступен", "Markdown exporter", "Output записан"))
    assert_clean_page(page)


def test_interviews_and_algorithms_modes_are_reachable(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Interviews")

    for mode in ("Learn", "Practice", "Timed Mock", "Review"):
        click_visible_button_containing(page, mode)
        assert_clean_page(page)
    assert body_has_any(page, ("Interviews", "Вопросов", "Answer notes", "Ответь"))

    click_nav(page, "Algorithms")
    expect(page.locator("body")).to_contain_text("Interview Arena", timeout=10_000)
    for mode in ("Learn", "Practice", "Timed Mock", "Review"):
        click_visible_button_containing(page, mode)
        assert_clean_page(page)
    assert body_has_any(page, ("Algorithms", "Interview Arena", "Режим"))


@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)])
def test_home_and_ml_lab_responsive_navigation(
    page: Page,
    streamlit_app_url: str,
    viewport: tuple[int, int],
) -> None:
    width, height = viewport
    page.set_viewport_size({"width": width, "height": height})
    page.goto(streamlit_app_url, wait_until="domcontentloaded", timeout=20_000)
    expect(page.locator("body")).to_contain_text("Hub_ML", timeout=30_000)
    assert body_has_any(page, ("Продолжить", "План на сегодня", "Quality Gate"))
    assert_clean_page(page)
    assert_no_horizontal_overflow(page)

    click_nav(page, "ML Lab")
    expect(page.locator("body")).to_contain_text("ML Lab", timeout=10_000)
    expect(page.locator("body")).to_contain_text("Шаги проекта", timeout=10_000)
    assert body_has_any(page, ("Перед стартом", "Experiment Tracker Lite", "Каталог проектов"))
    assert_clean_page(page)
    assert_no_horizontal_overflow(page)
