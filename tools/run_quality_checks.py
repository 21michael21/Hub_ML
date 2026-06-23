from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)

INSTALL_PLAYWRIGHT = (
    "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pip install -r requirements-dev.txt\n"
    "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m playwright install chromium"
)

Mode = Literal["quick", "ui", "content", "full"]
Status = Literal["PASS", "FAIL", "SKIP"]


@dataclass(frozen=True)
class Check:
    check_id: str
    label: str
    command: tuple[str, ...] | None = None
    required: bool = True
    callable_name: str | None = None


@dataclass(frozen=True)
class CheckResult:
    check: Check
    status: Status
    returncode: int
    output: str = ""
    reason: str = ""


def python_cmd(*args: str) -> tuple[str, ...]:
    return (str(PYTHON), *args)


def quick_checks() -> list[Check]:
    return [
        Check(
            "compile",
            "Compile app/core/tools/tests",
            python_cmd("-m", "compileall", "app.py", "core", "tools", "tests"),
        ),
        Check(
            "pytest",
            "Pytest without browser E2E",
            python_cmd("-m", "pytest", "-q", "--ignore=tests/e2e"),
        ),
        Check("app_import", "App import", python_cmd("-c", "import app; print('APP_IMPORT_OK')")),
        Check("resources", "Validate resources", python_cmd("tools/validate_resources.py")),
    ]


def ui_checks(*, strict_e2e: bool = False) -> list[Check]:
    return [
        Check(
            "apptest",
            "Streamlit AppTest smoke",
            python_cmd("-m", "pytest", "tests/test_app_smoke.py", "-q"),
        ),
        Check(
            "raw_html",
            "Raw HTML AppTest sweep",
            python_cmd("-m", "pytest", "tests/test_app_smoke.py", "-q", "-k", "raw_html"),
        ),
        Check(
            "e2e",
            "Playwright browser E2E",
            python_cmd("-m", "pytest", "tests/e2e", "-q"),
            required=strict_e2e,
        ),
    ]


def content_checks() -> list[Check]:
    checks = [
        Check("content_gate", "Content gate", python_cmd("tools/check_content_gate.py", "--reaudit")),
        Check("internal_links", "Internal UI links", python_cmd("tools/check_internal_links.py")),
        Check("language", "Russian content language audit", python_cmd("tools/check_content_language.py")),
    ]
    if (ROOT / "tools" / "check_required_topic_sources.py").exists():
        checks.append(
            Check(
                "required_sources",
                "Required topic source readiness",
                python_cmd("tools/check_required_topic_sources.py"),
            )
        )
    return checks


def smoke_checks() -> list[Check]:
    return [
        Check("dataset_registry", "Dataset registry smoke", callable_name="dataset_registry_smoke"),
        Check("mentor_tasks", "Mentor task loading smoke", callable_name="mentor_task_smoke"),
        Check(
            "df_events_task",
            "df_events task runner smoke",
            required=False,
            callable_name="df_events_task_runner_smoke",
        ),
    ]


def build_plan(mode: Mode, *, strict_e2e: bool = False) -> list[Check]:
    checks = quick_checks()
    if mode == "quick":
        return checks
    if mode == "ui":
        return checks + ui_checks(strict_e2e=strict_e2e)
    if mode == "content":
        return checks + content_checks()
    if mode == "full":
        return checks + ui_checks(strict_e2e=strict_e2e) + content_checks() + smoke_checks()
    raise ValueError(f"unknown mode: {mode}")


def playwright_ready() -> tuple[bool, str]:
    if importlib.util.find_spec("playwright") is None:
        return False, "pytest-playwright is not installed"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:  # noqa: BLE001 - dependency/browser availability probe only.
        return False, f"Playwright Chromium is not ready: {exc}"
    return True, "Playwright Chromium is ready"


def run_subprocess(command: tuple[str, ...]) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout


def dataset_registry_smoke() -> tuple[int, str]:
    from core.datasets.registry import scan_datasets

    datasets = scan_datasets(ROOT / "datasets")
    names = {str(dataset.get("name")) for dataset in datasets}
    required = {"df_events.csv", "df_matching.csv", "df_orders.csv"}
    missing = sorted(required - names)
    if missing:
        return 1, f"missing datasets: {', '.join(missing)}"
    return 0, f"datasets OK: {', '.join(sorted(required))}"


def mentor_task_smoke() -> tuple[int, str]:
    from core.tasks.loader import load_mentor_tasks

    data = load_mentor_tasks(ROOT / "content" / "extracted" / "mentor_tasks.json")
    tasks = data.get("tasks", [])
    if not tasks:
        return 1, "mentor tasks not loaded"
    return 0, f"mentor tasks OK: {len(tasks)} loaded, {data.get('skipped', 0)} skipped"


def df_events_task_runner_smoke() -> tuple[int, str]:
    return 0, "optional smoke skipped: task execution uses the live kernel and is intentionally not mutated here"


CALLABLE_CHECKS: dict[str, Callable[[], tuple[int, str]]] = {
    "dataset_registry_smoke": dataset_registry_smoke,
    "mentor_task_smoke": mentor_task_smoke,
    "df_events_task_runner_smoke": df_events_task_runner_smoke,
}


def run_check(check: Check, *, strict_e2e: bool = False) -> CheckResult:
    if check.check_id == "e2e":
        ready, reason = playwright_ready()
        if not ready and not strict_e2e:
            return CheckResult(
                check=check,
                status="SKIP",
                returncode=0,
                reason=f"{reason}\nInstall with:\n{INSTALL_PLAYWRIGHT}",
            )
        if not ready:
            return CheckResult(check=check, status="FAIL", returncode=1, reason=reason)

    if check.callable_name:
        returncode, output = CALLABLE_CHECKS[check.callable_name]()
    elif check.command:
        returncode, output = run_subprocess(check.command)
    else:
        return CheckResult(check=check, status="FAIL", returncode=1, reason="check has no command")

    if returncode == 0:
        return CheckResult(check=check, status="PASS", returncode=returncode, output=output)
    return CheckResult(check=check, status="FAIL", returncode=returncode, output=output)


def command_text(command: tuple[str, ...] | None) -> str:
    if command is None:
        return "<python callable>"
    return " ".join(command)


def print_plan(checks: list[Check]) -> None:
    for check in checks:
        requirement = "required" if check.required else "optional"
        print(f"{check.check_id:18} {requirement:8} {command_text(check.command)}")


def print_summary(results: list[CheckResult]) -> None:
    print("\nQuality check summary")
    print("=====================")
    for result in results:
        marker = {"PASS": "✓", "FAIL": "✗", "SKIP": "-"}[result.status]
        requirement = "required" if result.check.required else "optional"
        print(f"{marker} {result.status:4} {result.check.check_id:18} ({requirement}) {result.check.label}")
        if result.reason:
            print(indent(result.reason.strip()))
        elif result.output.strip():
            lines = result.output.strip().splitlines()
            tail = lines[-3:]
            print(indent("\n".join(tail)))


def indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in text.splitlines())


def run_checks(checks: list[Check], *, strict_e2e: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check in checks:
        print(f"\n▶ {check.label}")
        result = run_check(check, strict_e2e=strict_e2e)
        results.append(result)
        print(f"{result.status}: {check.check_id}")
        if result.status == "SKIP" and result.reason:
            print(indent(result.reason.strip()))
        elif result.output.strip():
            print(indent(result.output.strip().splitlines()[-1]))
    return results


def has_required_failures(results: list[CheckResult]) -> bool:
    return any(result.status == "FAIL" and result.check.required for result in results)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unified local Hub_ML quality checks.")
    parser.add_argument("--mode", choices=("quick", "ui", "content", "full"), default="quick")
    parser.add_argument("--strict-e2e", action="store_true", help="Fail if Playwright E2E cannot run.")
    parser.add_argument("--dry-run", action="store_true", help="Print the selected checks without running them.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    checks = build_plan(args.mode, strict_e2e=args.strict_e2e)
    print(f"Hub_ML quality checks: mode={args.mode} strict_e2e={args.strict_e2e}")
    if args.dry_run:
        print_plan(checks)
        return 0

    results = run_checks(checks, strict_e2e=args.strict_e2e)
    print_summary(results)
    return 1 if has_required_failures(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
