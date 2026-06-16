from __future__ import annotations

import base64
import binascii
import io
from typing import Any

import streamlit as st


def notebook_output_from_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    msg_type = msg.get("header", {}).get("msg_type")
    content = msg.get("content", {})

    if msg_type == "stream":
        return {
            "type": "stream",
            "name": content.get("name", "stdout"),
            "text": content.get("text", ""),
        }

    if msg_type in {"execute_result", "display_data"}:
        data = content.get("data", {})
        return {
            "type": msg_type,
            "data": data,
            "text": data.get("text/plain", ""),
            "metadata": content.get("metadata", {}),
        }

    if msg_type == "error":
        return {
            "type": "error",
            "ename": content.get("ename", ""),
            "evalue": content.get("evalue", ""),
            "traceback": content.get("traceback", []),
        }

    return None


def outputs_to_stdout(outputs: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for output in outputs:
        if output.get("type") == "stream" and output.get("name") == "stdout":
            chunks.append(str(output.get("text") or ""))
    return "".join(chunks)


def mime_payload_to_text(value: Any) -> str:
    if isinstance(value, list):
        return "".join(str(item) for item in value)
    return str(value or "")


def render_notebook_rich_data(data: dict[str, Any], output_type: str) -> None:
    if not isinstance(data, dict):
        st.code(str(data), language="text")
        return

    png_payload = data.get("image/png")
    if png_payload:
        try:
            image_bytes = base64.b64decode(mime_payload_to_text(png_payload), validate=False)
            st.caption("image/png")
            st.image(io.BytesIO(image_bytes))
            return
        except (binascii.Error, ValueError, OSError) as exc:
            st.warning(f"Не удалось отрисовать image/png: {exc}")

    html_payload = data.get("text/html")
    if html_payload:
        st.caption("text/html")
        st.markdown(mime_payload_to_text(html_payload), unsafe_allow_html=True)
        return

    plain_payload = data.get("text/plain")
    if plain_payload:
        st.caption("result" if output_type == "execute_result" else "display")
        st.code(mime_payload_to_text(plain_payload), language="text")
        return

    st.caption(f"{output_type}: нет поддерживаемого вывода")


def render_notebook_output(output: dict[str, Any]) -> None:
    output_type = output.get("type")

    if output_type == "stream":
        name = str(output.get("name") or "stdout")
        text = str(output.get("text") or "")
        if name == "status":
            st.info(text)
        else:
            st.caption(name)
            st.code(text, language="text")
        return

    if output_type in {"execute_result", "display_data"}:
        render_notebook_rich_data(output.get("data", {}), str(output_type))
        return

    if output_type == "error":
        ename = str(output.get("ename") or "Error")
        evalue = str(output.get("evalue") or "")
        traceback_lines = output.get("traceback") or []
        st.error(f"{ename}: {evalue}".strip())
        if traceback_lines:
            st.code("\n".join(str(line) for line in traceback_lines), language="text")
        return

    st.code(str(output), language="text")
