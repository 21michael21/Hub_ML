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
            const buttons = Array.from(document.querySelectorAll('button'));
            const target = buttons.find((button) => {
                const label = (button.innerText || button.textContent || '').trim();
                const rect = button.getBoundingClientRect();
                return label.includes(text) && rect.width > 0 && rect.height > 0 && !button.disabled;
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
    clicked = click_visible_button_containing(page, label)
    assert clicked is not None, f"Navigation button not found: {label}"


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

    after = visible_text(page)
    assert after != before
    assert "Theory" in after
    assert_clean_page(page)


def test_theory_backlink_click_opens_source_note(page: Page, streamlit_app_url: str) -> None:
    open_theory_from_home(page, streamlit_app_url)

    outgoing_clicked = click_visible_graph_link(page)
    assert outgoing_clicked is not None, "Need an outgoing link target with backlinks"
    expect(page.locator("body")).to_contain_text("Открыть случайную непройденную заметку", timeout=10_000)
    before = visible_text(page)

    backlink_clicked = click_visible_graph_link(page, require_path_label=True)
    assert backlink_clicked is not None, "Expected a backlink button on the target note"
    after = visible_text(page)

    assert after != before
    assert "Theory" in after
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
    assert any(marker in text for marker in ("PROJECT DETAIL", "Milestone progress", "milestone", "Experiment Tracker Lite"))
    assert_clean_page(page)
