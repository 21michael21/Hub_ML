from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REAL_VAULT = Path("/Users/mihailkulibaba/Projects/practic_ML/obsidian_vkat")
ARTIFACTS_DIR = Path(__file__).with_name("artifacts")


def _pick_port(preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _make_tiny_vault(root: Path) -> Path:
    vault = root / "vault"
    atlas = vault / "00_Atlas"
    atlas.mkdir(parents=True, exist_ok=True)
    (vault / "welcome.md").write_text(
        """---
title: Welcome
tags: [e2e]
---

# Welcome

Small E2E vault note.
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
    return vault


def _wait_for_server(url: str, process: subprocess.Popen[str], timeout: float = 35.0) -> tuple[bool, str]:
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
    return False, output


@pytest.fixture(scope="session")
def streamlit_app_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    port = _pick_port(int(os.environ.get("HUB_ML_E2E_PORT", "8765")))
    run_root = tmp_path_factory.mktemp("hub_ml_e2e_state")
    vault = Path(
        os.environ.get("HUB_ML_E2E_VAULT")
        or os.environ.get("VAULT_PATH")
        or str(DEFAULT_REAL_VAULT)
    )
    if not vault.exists():
        vault = _make_tiny_vault(tmp_path_factory.mktemp("hub_ml_e2e"))

    env = os.environ.copy()
    env.update(
        {
            "VAULT_PATH": str(vault),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HUB_ML_PROGRESS_PATH": str(run_root / ".learning_progress.json"),
            "HUB_ML_USER_PROJECTS_DIR": str(run_root / "user_projects"),
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
    started, output = _wait_for_server(url, process)
    if not started:
        process.terminate()
        pytest.skip(f"Streamlit test server did not start. Output: {output[-1000:]}")

    yield url

    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or report.passed:
        return
    page = item.funcargs.get("page")
    if page is None:
        return
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = ARTIFACTS_DIR / f"{item.name}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        return
