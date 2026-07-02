from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from core.datasets.registry import scan_datasets
from playwright.sync_api import Page, expect


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ERROR_MARKERS = ("Traceback", "TypeError", "Exception")


def body_text(page: Page) -> str:
    return page.locator("body").inner_text(timeout=10_000)


def assert_no_runtime_errors(page: Page) -> None:
    text = body_text(page)
    for marker in RUNTIME_ERROR_MARKERS:
        assert marker not in text


def open_app(page: Page, app_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(app_url, wait_until="domcontentloaded", timeout=20_000)
    expect(page.locator("body")).to_contain_text("Hub_ML", timeout=30_000)
    expect(page.locator("body")).to_contain_text("local ML workstation", timeout=30_000)
    expect(page.locator("body")).to_contain_text("Открыть теорию", timeout=30_000)


def enable_admin_mode(page: Page) -> None:
    page.evaluate(
        """() => {
            const labels = Array.from(document.querySelectorAll('label'));
            const admin = labels.find((label) => (label.innerText || label.textContent || '').includes('Админ'));
            if (admin) admin.click();
        }"""
    )
    page.wait_for_timeout(600)
    assert_no_runtime_errors(page)


def click_nav(page: Page, label_fragment: str) -> None:
    if label_fragment == "Home" and re.search(r"\bHome\b", body_text(page)):
        assert_no_runtime_errors(page)
        return

    clicked = page.evaluate(
        """label => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const target = buttons.find((button) => (button.innerText || button.textContent || '').includes(label));
            if (!target) {
                return { clicked: false, labels: buttons.map((button) => (button.innerText || button.textContent || '').trim()) };
            }
            target.click();
            return { clicked: true, labels: [] };
        }""",
        label_fragment,
    )
    if not clicked["clicked"]:
        enable_admin_mode(page)
        clicked = page.evaluate(
            """label => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const target = buttons.find((button) => (button.innerText || button.textContent || '').includes(label));
                if (!target) {
                    return { clicked: false, labels: buttons.map((button) => (button.innerText || button.textContent || '').trim()) };
                }
                target.click();
                return { clicked: true, labels: [] };
            }""",
            label_fragment,
        )
    assert clicked["clicked"], f"Could not find nav button {label_fragment!r}. Buttons: {clicked['labels']}"
    page.wait_for_timeout(500)
    assert_no_runtime_errors(page)


def test_home_page_no_traceback(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    text = body_text(page)

    assert "Hub_ML" in text or "Learning Sandbox" in text
    for marker in RUNTIME_ERROR_MARKERS:
        assert marker not in text
    assert "<div class=" not in text
    assert "section-eyebrow" not in text


def test_core_navigation_sections_open(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)

    for label in (
        "Home",
        "Theory",
        "Practice",
        "Tasks",
        "Datasets",
        "Notebook",
        "Data Lab",
        "Portfolio",
    ):
        click_nav(page, label)


def test_data_lab_projects_no_widget_key_crash(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Data Lab")

    text = body_text(page)
    assert "safe_widget_key" not in text
    assert "takes 2 positional arguments" not in text
    assert "TypeError" not in text
    assert re.search(r"Baseline classifier конверсии заказов|EDA-отчёт по заказам|Project Catalog", text)


def test_home_links_do_not_break(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)

    open_note = page.get_by_role("button", name="Открыть теорию")
    expect(open_note).to_have_count(1, timeout=10_000)
    open_note.click()
    page.wait_for_timeout(800)

    assert_no_runtime_errors(page)
    assert re.search(r"\\.md|Knowledge Map|Welcome|Theory", body_text(page))


def test_datasets_visible(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Datasets")

    assert_no_runtime_errors(page)
    expect(page.locator("body")).to_contain_text("CSV-файлы из папки", timeout=10_000)
    dataset_names = {dataset["name"] for dataset in scan_datasets(ROOT / "datasets")}
    assert {"df_events.csv", "df_matching.csv", "df_orders.csv"}.issubset(dataset_names)


def test_tasks_page_smoke(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Tasks")

    assert_no_runtime_errors(page)
    assert re.search(r"Tasks|Mentor", body_text(page))


def test_theory_quality_smoke(page: Page, streamlit_app_url: str) -> None:
    open_app(page, streamlit_app_url)
    click_nav(page, "Theory Quality")

    assert_no_runtime_errors(page)
    assert "Theory Quality" in body_text(page)
