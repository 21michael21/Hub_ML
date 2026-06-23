from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "tests" / "e2e" / "artifacts" / "screenshots"
DEFAULT_VAULT = ROOT / "tests" / "fixtures" / "sample_vault"
DEFAULT_PORT = 8766
RUNTIME_MARKERS = ("Traceback", "TypeError", "KeyError", "ImportError", "Exception")


@dataclass(frozen=True)
class ScreenshotTarget:
    name: str
    filename: str
    nav_label: str
    description: str


SCREENSHOT_TARGETS = [
    ScreenshotTarget("home-cockpit", "home-cockpit.png", "Home", "Home cockpit"),
    ScreenshotTarget("tasks-result", "tasks-result.png", "Tasks", "Tasks page/result panel"),
    ScreenshotTarget("projects-detail", "projects-detail.png", "Data Lab", "Project detail"),
    ScreenshotTarget("notebook-output", "notebook-output.png", "Notebook", "Notebook output area"),
    ScreenshotTarget("portfolio-export", "portfolio-export.png", "Portfolio", "Portfolio exporter"),
    ScreenshotTarget("interview-arena", "interview-arena.png", "Interviews", "Interview Arena"),
    ScreenshotTarget("theory-quality", "theory-quality.png", "Theory Quality", "Theory Quality reports"),
]

NAV_ALIASES = {
    "Home": ("Home",),
    "Tasks": ("Tasks", "✓ Tasks", "✓"),
    "Data Lab": ("Data Lab", "▣ Data Lab", "▣"),
    "Notebook": ("Notebook", "▦ Notebook", "▦"),
    "Portfolio": ("Portfolio", "□ Portfolio", "□"),
    "Interviews": ("Interviews", "? Interviews", "?"),
    "Theory Quality": ("Theory Quality", "◇ Theory Quality", "◇"),
}


def pick_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(url: str, process: subprocess.Popen[str], timeout: float = 45.0) -> tuple[bool, str]:
    deadline = time.time() + timeout
    output = ""
    while time.time() < deadline:
        if process.poll() is not None:
            if process.stdout:
                output += process.stdout.read() or ""
            return False, output
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return True, output
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    if process.stdout:
        output += process.stdout.read() or ""
    return False, output


def start_streamlit(vault: Path, port: int) -> tuple[subprocess.Popen[str], str]:
    env = os.environ.copy()
    env.update(
        {
            "VAULT_PATH": str(vault),
            "PYTHONDONTWRITEBYTECODE": "1",
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        }
    )
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ROOT / "app.py"),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    started, output = wait_for_server(url, process)
    if not started:
        process.terminate()
        raise RuntimeError(f"Streamlit did not start. Output: {output[-1200:]}")
    return process, url


def body_text(page: object) -> str:
    return page.locator("body").inner_text(timeout=10_000)


def assert_clean_page(page: object) -> None:
    text = body_text(page)
    found = [marker for marker in RUNTIME_MARKERS if marker in text]
    if found:
        raise AssertionError(f"Runtime marker(s) visible: {', '.join(found)}")


def click_button_containing(page: object, text: str) -> bool:
    result = page.evaluate(
        """({ text }) => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const target = buttons.find((button) => (button.innerText || button.textContent || '').includes(text));
            if (!target) return false;
            target.scrollIntoView({ block: 'center', inline: 'nearest' });
            target.click();
            return true;
        }""",
        {"text": text},
    )
    if not result:
        return False
    page.wait_for_timeout(900)
    assert_clean_page(page)
    return True


def click_first_available(page: object, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        if click_button_containing(page, label):
            return label
    return None


def open_app(page: object, url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(url, wait_until="domcontentloaded", timeout=25_000)
    page.wait_for_function(
        """() => {
            const text = document.body?.innerText || "";
            return text.includes("Hub_ML") || text.includes("Learning Sandbox");
        }""",
        timeout=30_000,
    )
    page.wait_for_timeout(2200)
    assert_clean_page(page)


def click_nav(page: object, label: str) -> None:
    if label == "Home" and "Hub_ML" in body_text(page):
        return
    clicked = click_first_available(page, NAV_ALIASES.get(label, (label,)))
    if clicked is None:
        labels = page.evaluate(
            """() => Array.from(document.querySelectorAll('button'))
                .map((button) => (button.innerText || button.textContent || '').trim())
                .slice(0, 80)"""
        )
        raise AssertionError(f"Navigation item not found: {label}. Buttons: {labels}")


def prepare_target(page: object, target: ScreenshotTarget) -> None:
    click_nav(page, target.nav_label)
    if target.name == "projects-detail":
        click_first_available(page, ("Open project", "Открыть проект", "Select project"))
    elif target.name == "portfolio-export":
        click_first_available(page, ("Markdown preview", "Preview"))
    elif target.name == "notebook-output":
        click_first_available(page, ("Обновить вывод", "Output"))
    page.wait_for_timeout(1000)
    assert_clean_page(page)


def capture_screenshots(
    *,
    output_dir: Path,
    vault: Path,
    port: int,
    headed: bool = False,
    start_server: Callable[[Path, int], tuple[subprocess.Popen[str], str]] = start_streamlit,
) -> list[Path]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    process, url = start_server(vault, port)
    captured: list[Path] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not headed)
            page = browser.new_page()
            open_app(page, url)
            for target in SCREENSHOT_TARGETS:
                prepare_target(page, target)
                destination = output_dir / target.filename
                page.screenshot(path=str(destination), full_page=True)
                captured.append(destination)
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    return captured


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture manual visual QA screenshots for Hub_ML.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--vault", default=os.environ.get("VAULT_PATH", str(DEFAULT_VAULT)))
    parser.add_argument("--port", type=int, default=int(os.environ.get("HUBML_SCREENSHOT_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--headed", action="store_true", help="Show Chromium while capturing.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print targets without launching Streamlit or Playwright.",
    )
    return parser.parse_args(argv)


def main_from_args(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).expanduser()
    vault = Path(args.vault).expanduser()
    if args.dry_run:
        print(f"output_dir={output_dir}")
        print(f"vault={vault}")
        for target in SCREENSHOT_TARGETS:
            print(f"{target.filename}: {target.description} ({target.nav_label})")
        return 0
    if not vault.exists():
        raise SystemExit(f"Vault path does not exist: {vault}")
    port = pick_port(args.port)
    captured = capture_screenshots(output_dir=output_dir, vault=vault, port=port, headed=args.headed)
    print("Captured screenshots:")
    for path in captured:
        print(f"- {path}")
    return 0


def main() -> int:
    return main_from_args()


if __name__ == "__main__":
    raise SystemExit(main())
