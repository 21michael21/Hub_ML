from __future__ import annotations

from typing import Any

from core.notebook.kernel import run_code_in_kernel_sync


def build_mentor_task_script(solution_code: str, test_code: str, setup_code: str = "") -> str:
    parts: list[str] = []
    setup_code = str(setup_code or "").strip()
    solution_code = str(solution_code or "").rstrip()
    test_code = str(test_code or "").strip()

    if setup_code:
        parts.append("# --- setup ---\n" + setup_code)
    parts.append("# --- solution ---\n" + solution_code)
    if test_code:
        parts.append("# --- tests ---\n" + test_code)
    return "\n\n".join(parts).rstrip() + "\n"


def first_error_output(result: dict[str, Any]) -> dict[str, Any]:
    outputs = result.get("outputs") if isinstance(result.get("outputs"), list) else []
    return next(
        (output for output in outputs if isinstance(output, dict) and output.get("type") == "error"),
        {},
    )


def classify_task_result(result: dict[str, Any]) -> str:
    if result.get("timed_out"):
        return "TIMEOUT"
    error = str(result.get("error") or "")
    if error == "KernelBusy":
        return "KERNEL_BUSY"
    if result.get("ok"):
        return "PASS"

    error_output = first_error_output(result)
    ename = str(error_output.get("ename") or error)
    if ename == "AssertionError":
        return "FAIL"
    return "ERROR"


def traceback_text(error_output: dict[str, Any]) -> str:
    traceback_lines = error_output.get("traceback") or []
    if traceback_lines:
        return "\n".join(str(line) for line in traceback_lines)
    ename = str(error_output.get("ename") or "")
    evalue = str(error_output.get("evalue") or "")
    return f"{ename}: {evalue}".strip()


def run_code_in_notebook_kernel_sync(code: str, timeout_seconds: int = 20) -> dict[str, Any]:
    result = run_code_in_kernel_sync(code, timeout_seconds=timeout_seconds)
    result["classification"] = classify_task_result(result)
    return result
