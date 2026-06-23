from __future__ import annotations

import logging
import queue
import time
from pathlib import Path
from typing import Any

import streamlit as st

from core.notebook.output import notebook_output_from_message, outputs_to_stdout

logger = logging.getLogger(__name__)

try:
    from jupyter_client import KernelManager
except ImportError:
    KernelManager = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@st.cache_resource(show_spinner=False)
def get_notebook_runtime() -> dict[str, Any]:
    return {"kernel_state": None, "outputs": {}}


def run_hidden_kernel_setup(kc: Any) -> None:
    try:
        msg_id = kc.execute(
            'get_ipython().run_line_magic("matplotlib", "inline")',
            store_history=False,
            silent=True,
            allow_stdin=False,
        )
        started = time.perf_counter()
        while time.perf_counter() - started < 4:
            try:
                msg = kc.get_iopub_msg(timeout=0.2)
            except queue.Empty:
                continue
            if msg.get("parent_header", {}).get("msg_id") != msg_id:
                continue
            if (
                msg.get("header", {}).get("msg_type") == "status"
                and msg.get("content", {}).get("execution_state") == "idle"
            ):
                break
    except Exception:
        logger.debug("Hidden notebook kernel setup failed.", exc_info=True)


def start_notebook_kernel() -> dict[str, Any]:
    if KernelManager is None:
        return {
            "km": None,
            "kc": None,
            "status": "dead",
            "busy_cell_id": None,
            "last_error": "jupyter_client/ipykernel не установлены.",
        }

    runtime = get_notebook_runtime()
    kernel_state = runtime.get("kernel_state")
    if isinstance(kernel_state, dict):
        km = kernel_state.get("km")
        if km is not None and getattr(km, "is_alive", lambda: False)():
            st.session_state["notebook_kernel_state"] = kernel_state
            return kernel_state

    try:
        km = KernelManager()
        km.start_kernel(cwd=str(PROJECT_ROOT))
        kc = km.client()
        kc.start_channels()
        kc.wait_for_ready(timeout=12)
        run_hidden_kernel_setup(kc)
        kc.stop_channels()
    except Exception as exc:
        return {
            "km": None,
            "kc": None,
            "status": "dead",
            "busy_cell_id": None,
            "last_error": str(exc),
        }

    kernel_state = {
        "km": km,
        "kc": None,
        "status": "idle",
        "busy_cell_id": None,
        "active_execution": None,
        "last_error": "",
    }
    runtime["kernel_state"] = kernel_state
    st.session_state["notebook_kernel_state"] = kernel_state
    return kernel_state


def refresh_notebook_kernel_state() -> dict[str, Any]:
    kernel_state = start_notebook_kernel()
    km = kernel_state.get("km")

    if km is None or not getattr(km, "is_alive", lambda: False)():
        kernel_state["status"] = "dead"
        kernel_state["busy_cell_id"] = None
        return kernel_state

    if kernel_state.get("active_execution"):
        kernel_state["status"] = "busy"
    elif kernel_state.get("status") == "busy":
        kernel_state["status"] = "idle"
        kernel_state["busy_cell_id"] = None

    return kernel_state


def shutdown_notebook_kernel(kernel_state: dict[str, Any]) -> None:
    km = kernel_state.get("km")
    kc = kernel_state.get("kc")
    active = kernel_state.get("active_execution")
    if isinstance(active, dict):
        active_kc = active.get("kc")
        try:
            if active_kc is not None:
                active_kc.stop_channels()
        except Exception:
            logger.debug("Failed to stop active notebook kernel channels.", exc_info=True)
    try:
        if kc is not None:
            kc.stop_channels()
    except Exception:
        logger.debug("Failed to stop notebook kernel channels.", exc_info=True)
    try:
        if km is not None and getattr(km, "is_alive", lambda: False)():
            km.shutdown_kernel(now=True)
    except Exception:
        logger.debug("Failed to shut down notebook kernel.", exc_info=True)


def restart_notebook_kernel() -> None:
    runtime = get_notebook_runtime()
    kernel_state = runtime.get("kernel_state")
    if isinstance(kernel_state, dict):
        shutdown_notebook_kernel(kernel_state)

    runtime["kernel_state"] = None
    runtime["outputs"] = {}
    st.session_state["notebook_outputs"] = runtime["outputs"]
    start_notebook_kernel()


def interrupt_notebook_kernel() -> None:
    kernel_state = refresh_notebook_kernel_state()
    km = kernel_state.get("km")
    try:
        if km is not None and getattr(km, "is_alive", lambda: False)():
            km.interrupt_kernel()
            kernel_state["last_error"] = ""
    except Exception as exc:
        kernel_state["last_error"] = f"Не удалось прервать ядро: {exc}"


def finish_notebook_execution(kernel_state: dict[str, Any]) -> None:
    active = kernel_state.get("active_execution")
    if not isinstance(active, dict):
        return

    kc = active.get("kc")
    cell_id = active.get("cell_id")
    outputs = active.get("outputs", [])
    runtime = get_notebook_runtime()
    runtime.setdefault("outputs", {})[cell_id] = outputs
    st.session_state["notebook_outputs"] = runtime["outputs"]

    try:
        if kc is not None:
            kc.stop_channels()
    except Exception:
        logger.debug("Failed to stop active execution channels.", exc_info=True)

    kernel_state["active_execution"] = None
    kernel_state["status"] = "idle"
    kernel_state["busy_cell_id"] = None


def poll_notebook_execution(kernel_state: dict[str, Any], time_budget: float = 0.12) -> None:
    active = kernel_state.get("active_execution")
    if not isinstance(active, dict):
        return

    km = kernel_state.get("km")
    kc = active.get("kc")
    msg_id = active.get("msg_id")
    cell_id = active.get("cell_id")
    outputs: list[dict[str, Any]] = active.setdefault("outputs", [])
    runtime = get_notebook_runtime()
    output_store = runtime.setdefault("outputs", {})
    started = time.perf_counter()
    active.setdefault("started_at", started)

    if kc is None or msg_id is None or cell_id is None:
        finish_notebook_execution(kernel_state)
        return

    while time.perf_counter() - started < time_budget:
        try:
            shell_msg = kc.get_shell_msg(timeout=0.01)
        except queue.Empty:
            shell_msg = None

        if shell_msg and shell_msg.get("parent_header", {}).get("msg_id") == msg_id:
            active["shell_done"] = True
            active["last_message_at"] = time.perf_counter()

        if active.get("shell_done") and time.perf_counter() - active.get("last_message_at", started) > 0.35:
            finish_notebook_execution(kernel_state)
            return

        if km is None or not getattr(km, "is_alive", lambda: False)():
            outputs.append(
                {
                    "type": "error",
                    "ename": "KernelDead",
                    "evalue": "Python-ядро остановилось. Перезапустите его.",
                    "traceback": [],
                }
            )
            output_store[cell_id] = outputs
            kernel_state["status"] = "dead"
            kernel_state["busy_cell_id"] = None
            kernel_state["active_execution"] = None
            return

        try:
            msg = kc.get_iopub_msg(timeout=0.03)
        except queue.Empty:
            quiet_after_output = (
                bool(outputs)
                and time.perf_counter() - active.get("last_message_at", started) > 2.0
            )
            if quiet_after_output:
                finish_notebook_execution(kernel_state)
                return
            continue

        if msg.get("parent_header", {}).get("msg_id") != msg_id:
            continue

        active["last_message_at"] = time.perf_counter()
        msg_type = msg.get("header", {}).get("msg_type")
        if msg_type == "status":
            execution_state = msg.get("content", {}).get("execution_state")
            if execution_state == "idle":
                finish_notebook_execution(kernel_state)
                return
            kernel_state["status"] = "busy"
            continue

        output = notebook_output_from_message(msg)
        if output is not None:
            outputs.append(output)
            output_store[cell_id] = outputs
            st.session_state["notebook_outputs"] = output_store


def start_notebook_cell(cell_id: str, code: str) -> None:
    kernel_state = refresh_notebook_kernel_state()
    if kernel_state.get("status") == "busy":
        return

    km = kernel_state.get("km")
    runtime = get_notebook_runtime()
    output_store = runtime.setdefault("outputs", {})
    st.session_state["notebook_outputs"] = output_store
    output_store[cell_id] = [
        {
            "type": "stream",
            "name": "status",
            "text": "Выполняется...",
        }
    ]

    if km is None or not getattr(km, "is_alive", lambda: False)():
        output_store[cell_id] = [
            {
                "type": "error",
                "ename": "KernelUnavailable",
                "evalue": kernel_state.get("last_error", "Jupyter kernel недоступен."),
                "traceback": [],
            }
        ]
        kernel_state["status"] = "dead"
        return

    try:
        kc = km.client()
        kc.start_channels()
        msg_id = kc.execute(code, store_history=True, allow_stdin=False)
    except Exception as exc:
        output_store[cell_id] = [
            {
                "type": "error",
                "ename": exc.__class__.__name__,
                "evalue": str(exc),
                "traceback": [],
            }
        ]
        kernel_state["status"] = "idle"
        kernel_state["busy_cell_id"] = None
        return

    kernel_state["status"] = "busy"
    kernel_state["busy_cell_id"] = cell_id
    kernel_state["active_execution"] = {
        "cell_id": cell_id,
        "kc": kc,
        "msg_id": msg_id,
        "outputs": [],
        "shell_done": False,
        "last_message_at": time.perf_counter(),
    }


def run_code_in_kernel_sync(code: str, timeout_seconds: int = 20) -> dict[str, Any]:
    started = time.perf_counter()
    kernel_state = refresh_notebook_kernel_state()
    if kernel_state.get("status") == "busy":
        return {
            "ok": False,
            "timed_out": False,
            "outputs": [
                {
                    "type": "error",
                    "ename": "KernelBusy",
                    "evalue": "Notebook kernel занят другой ячейкой. Дождитесь завершения или прервите выполнение.",
                    "traceback": [],
                }
            ],
            "stdout": "",
            "error": "KernelBusy",
            "elapsed": 0.0,
        }

    km = kernel_state.get("km")
    if km is None or not getattr(km, "is_alive", lambda: False)():
        return {
            "ok": False,
            "timed_out": False,
            "outputs": [
                {
                    "type": "error",
                    "ename": "KernelUnavailable",
                    "evalue": kernel_state.get("last_error", "Jupyter kernel недоступен."),
                    "traceback": [],
                }
            ],
            "stdout": "",
            "error": "KernelUnavailable",
            "elapsed": 0.0,
        }

    outputs: list[dict[str, Any]] = []
    kc = None
    try:
        kc = km.client()
        kc.start_channels()
        msg_id = kc.execute(code, store_history=True, allow_stdin=False)
        shell_done = False
        while True:
            elapsed = time.perf_counter() - started
            if elapsed > timeout_seconds:
                try:
                    km.interrupt_kernel()
                except Exception:
                    logger.debug("Failed to interrupt timed-out notebook kernel.", exc_info=True)
                drain_deadline = time.perf_counter() + 3.0
                while time.perf_counter() < drain_deadline:
                    try:
                        msg = kc.get_iopub_msg(timeout=0.1)
                    except queue.Empty:
                        continue
                    if msg.get("parent_header", {}).get("msg_id") != msg_id:
                        continue
                    msg_type = msg.get("header", {}).get("msg_type")
                    if msg_type == "status" and msg.get("content", {}).get("execution_state") == "idle":
                        break
                outputs.append(
                    {
                        "type": "error",
                        "ename": "Timeout",
                        "evalue": f"Выполнение прервано после {timeout_seconds} сек.",
                        "traceback": [],
                    }
                )
                return {
                    "ok": False,
                    "timed_out": True,
                    "outputs": outputs,
                    "stdout": outputs_to_stdout(outputs),
                    "error": "Timeout",
                    "elapsed": elapsed,
                }

            try:
                shell_msg = kc.get_shell_msg(timeout=0.01)
            except queue.Empty:
                shell_msg = None
            if shell_msg and shell_msg.get("parent_header", {}).get("msg_id") == msg_id:
                shell_done = True

            try:
                msg = kc.get_iopub_msg(timeout=0.05)
            except queue.Empty:
                if shell_done:
                    break
                continue

            if msg.get("parent_header", {}).get("msg_id") != msg_id:
                continue

            msg_type = msg.get("header", {}).get("msg_type")
            if msg_type == "status" and msg.get("content", {}).get("execution_state") == "idle":
                break

            output = notebook_output_from_message(msg)
            if output is not None:
                outputs.append(output)

        error_output = next((output for output in outputs if output.get("type") == "error"), None)
        return {
            "ok": error_output is None,
            "timed_out": False,
            "outputs": outputs,
            "stdout": outputs_to_stdout(outputs),
            "error": error_output.get("ename") if error_output else "",
            "elapsed": time.perf_counter() - started,
        }
    except Exception as exc:
        outputs.append(
            {
                "type": "error",
                "ename": exc.__class__.__name__,
                "evalue": str(exc),
                "traceback": [],
            }
        )
        return {
            "ok": False,
            "timed_out": False,
            "outputs": outputs,
            "stdout": outputs_to_stdout(outputs),
            "error": exc.__class__.__name__,
            "elapsed": time.perf_counter() - started,
        }
    finally:
        try:
            if kc is not None:
                kc.stop_channels()
        except Exception:
            logger.debug("Failed to stop notebook cell channels.", exc_info=True)
