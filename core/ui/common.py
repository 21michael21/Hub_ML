from __future__ import annotations

import hashlib
import html
import re
from typing import Any
from urllib.parse import quote

import streamlit as st

from core.internal_links import InternalTarget


def safe_widget_key(*parts: object) -> str:
    raw_parts: list[str] = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip()
        if text:
            raw_parts.append(text)
    raw_key = "_".join(raw_parts) or "widget"
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", raw_key).strip("_")
    if not cleaned:
        cleaned = "widget"
    if len(cleaned) <= 110:
        return cleaned
    digest = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:10]
    return f"{cleaned[:96].rstrip('_')}_{digest}"




STATUS_CHIP_CLASSES = {
    "PASS": "status-chip-pass pass chip-pass",
    "FAIL": "status-chip-fail fail chip-fail",
    "ERROR": "status-chip-error error chip-error",
    "IN PROGRESS": "chip-in-progress",
    "DONE": "status-chip-pass pass chip-done",
    "NEEDS REVIEW": "chip-needs-review",
    "READY": "status-chip-pass pass chip-ready",
    "BLOCKED": "status-chip-error error chip-blocked",
}


UI_COMPONENT_RULES = {
    "action_button": "real_streamlit_button",
    "link_button": "real_streamlit_link_button",
    "static_chip": "metadata_only",
    "disabled_chip": "muted_with_reason",
    "metric_tile": "static_by_default",
    "card": "static_unless_action_is_explicit",
}


def ui_component_rules() -> dict[str, str]:
    return dict(UI_COMPONENT_RULES)


def render_html(markup: str) -> None:
    """Render trusted HTML returned by Hub_ML UI helpers only."""
    st.markdown(markup, unsafe_allow_html=True)


def normalize_chip_status(status: str) -> str:
    normalized = re.sub(r"[_\-]+", " ", str(status or "").strip().upper())
    aliases = {
        "PASSED": "PASS",
        "FAILED": "FAIL",
        "DOING": "IN PROGRESS",
        "READING": "IN PROGRESS",
        "TODO": "IN PROGRESS",
        "TO DO": "IN PROGRESS",
        "NOT STARTED": "IN PROGRESS",
        "REVIEW": "NEEDS REVIEW",
        "WEAK": "NEEDS REVIEW",
        "NOT_STARTED": "IN PROGRESS",
        "NOTSTARTED": "IN PROGRESS",
        "IDLE": "READY",
        "COMPLETE": "DONE",
        "COMPLETED": "DONE",
    }
    return aliases.get(normalized, normalized or "IN PROGRESS")


def render_status_chip(status: str) -> str:
    label = normalize_chip_status(status)
    css_class = STATUS_CHIP_CLASSES.get(label, "chip-info")
    return (
        f'<span class="status-chip static-chip {css_class}" aria-disabled="true">'
        f'<span class="chip-dot"></span>{html.escape(label)}</span>'
    )


def render_static_chip(label: str, value: str = "", *, status: str = "INFO") -> str:
    css_class = STATUS_CHIP_CLASSES.get(normalize_chip_status(status), "chip-info")
    value_markup = f'<span class="static-chip-value">{html.escape(str(value))}</span>' if value else ""
    return (
        f'<span class="status-chip static-chip {css_class}" aria-disabled="true">'
        f'<span class="chip-dot"></span>{html.escape(str(label))}{value_markup}</span>'
    )


def render_disabled_chip(label: str, reason: str) -> str:
    safe_reason = html.escape(str(reason or "Недоступно"))
    return (
        '<span class="status-chip static-chip disabled-chip chip-blocked" aria-disabled="true">'
        '<span><span class="chip-dot"></span>'
        f"{html.escape(str(label))}</span>"
        f'<span class="disabled-chip-reason">{safe_reason}</span>'
        "</span>"
    )


def render_section_eyebrow(label: str) -> str:
    return f'<div class="eyebrow section-eyebrow">{html.escape(str(label))}</div>'


def render_section_eyebrow_block(label: str) -> None:
    render_html(render_section_eyebrow(label))


def render_flat_section_header(
    title: str,
    description: str,
    *,
    eyebrow: str,
    status: str,
    caption: str = "",
) -> str:
    caption_markup = f'<div class="flat-section-caption">{html.escape(str(caption))}</div>' if caption else ""
    return (
        '<section class="flat-section-header section-fade">'
        f"{render_section_eyebrow(eyebrow)}"
        '<div class="flat-section-title-row">'
        f'<div class="flat-section-title">{html.escape(str(title))}</div>'
        f"{render_status_chip(status)}"
        "</div>"
        f'<div class="flat-section-desc">{html.escape(str(description))}</div>'
        f"{caption_markup}"
        "</section>"
    )


def render_section_header(
    title: str,
    description: str,
    *,
    eyebrow: str,
    status: str = "READY",
    caption: str = "",
) -> str:
    return render_flat_section_header(title, description, eyebrow=eyebrow, status=status, caption=caption)


def render_metric_tile(
    label: str,
    value: str | int | float,
    *,
    total: str | int | float | None = None,
    progress: float | None = None,
    meta: str = "",
    status: str = "",
) -> str:
    total_markup = f'<span class="metric-tile-total">/{html.escape(str(total))}</span>' if total is not None else ""
    bar_markup = ""
    if progress is not None:
        width = max(0.0, min(1.0, float(progress))) * 100
        fill_class = ""
        if status:
            fill_status = normalize_chip_status(status).lower().replace(" ", "-")
            fill_class = f" metric-fill-{html.escape(fill_status)}"
        bar_markup = (
            '<div class="bar metric-bar">'
            f'<i class="metric-bar-fill{fill_class}" style="width: {width:.1f}%"></i>'
            "</div>"
        )
    meta_markup = f'<div class="metric-tile-meta">{html.escape(str(meta))}</div>' if meta else ""
    return (
        '<div class="metric-tile">'
        f'<div class="n metric-tile-value">{html.escape(str(value))}{total_markup}</div>'
        f'<div class="metric-tile-label">{html.escape(str(label))}</div>'
        f"{meta_markup}{bar_markup}"
        "</div>"
    )


def render_action_button(
    label: str,
    *,
    key: str,
    on_click: Any | None = None,
    args: tuple[Any, ...] = (),
    href: str = "",
    disabled: bool = False,
    disabled_reason: str = "",
    help_text: str = "",
    use_container_width: bool = True,
) -> bool:
    if not disabled and on_click is None and not href:
        raise ValueError("render_action_button requires on_click or href for enabled actions")
    help_value = disabled_reason or help_text or href or None
    if href and on_click is None:
        st.link_button(
            label,
            href,
            key=key,
            help=help_value,
            disabled=disabled,
            type="primary",
            use_container_width=use_container_width,
        )
        return False
    return bool(
        st.button(
            label,
            key=key,
            help=help_value,
            disabled=disabled,
            type="primary",
            on_click=on_click if not disabled else None,
            args=args if not disabled else (),
            use_container_width=use_container_width,
        )
    )


def theory_note_query_href(relative_path: str) -> str:
    return f"?tab=Theory&note={quote(str(relative_path or ''), safe='')}"


def internal_target_tab_name(target: InternalTarget) -> str:
    kind = str(target.kind or "").strip()
    if kind == "theory_note":
        return "Theory"
    if kind == "task":
        return "🎯 Tasks"
    if kind == "practice":
        return "🎯 Practice"
    if kind in {"project", "milestone"}:
        return "🤖 ML Lab" if target.source == "ml_lab" else "🧪 Data Lab Projects"
    if kind == "dataset":
        return "📊 Datasets"
    if kind == "report":
        return "🧭 Theory Quality"
    return "Home"


def internal_target_query_href(target: InternalTarget) -> str:
    tab_name = internal_target_tab_name(target)
    if target.kind == "theory_note":
        return theory_note_query_href(target.path or target.target_id)

    params = [
        ("tab", tab_name),
        ("kind", str(target.kind or "")),
        ("target", target.target_id or target.path),
        ("project", target.project_id),
        ("milestone", target.milestone_id),
        ("source", target.source),
    ]
    query = "&".join(f"{name}={quote(str(value), safe='')}" for name, value in params if value)
    return f"?{query}"


def render_clickable_row(
    title: str,
    meta: str,
    *,
    href: str,
    action: str,
    status: str = "",
    accent: str = "",
) -> str:
    accent_class = f" clickable-row-{html.escape(str(accent).strip().casefold())}" if accent else ""
    status_markup = f" {render_status_chip(status)}" if status else ""
    return (
        f'<a class="clickable-row{accent_class}" href="{html.escape(str(href), quote=True)}" target="_self">'
        "<div>"
        f'<div class="clickable-row-title">{html.escape(str(title))}{status_markup}</div>'
        f'<div class="clickable-row-meta">{html.escape(str(meta))}</div>'
        "</div>"
        f'<div class="clickable-row-action">→ {html.escape(str(action))}</div>'
        "</a>"
    )


def render_internal_action_row(
    target: InternalTarget,
    title: str,
    subtitle: str,
    status: str,
    action_label: str = "Открыть",
) -> str:
    if target.exists:
        return render_clickable_row(
            title,
            subtitle,
            href=internal_target_query_href(target),
            action=action_label,
            status=status,
        )

    rendered_status = "BLOCKED" if target.disabled_reason else status
    status_markup = render_status_chip(rendered_status)
    meta = target.disabled_reason or subtitle
    return (
        '<div class="clickable-row disabled-target-card" aria-disabled="true">'
        "<div>"
        f'<div class="clickable-row-title">{html.escape(str(title))} {status_markup}</div>'
        f'<div class="clickable-row-meta">{html.escape(str(meta))}</div>'
        "</div>"
        f'<div class="clickable-row-action">{render_disabled_chip("Недоступно", meta)}</div>'
        "</div>"
    )


def render_card(
    title: str,
    body: str = "",
    *,
    eyebrow: str = "",
    meta: str = "",
    status: str = "",
    extra_class: str = "",
    content_html: str = "",
) -> str:
    classes = " ".join(["console-card", str(extra_class or "").strip()]).strip()
    eyebrow_markup = f'<div class="console-card-eyebrow">{html.escape(str(eyebrow))}</div>' if eyebrow else ""
    status_markup = render_status_chip(status) if status else ""
    body_markup = f'<div class="console-card-body">{html.escape(str(body))}</div>' if body else ""
    meta_markup = f'<div class="console-card-meta">{html.escape(str(meta))}</div>' if meta else ""
    return (
        f'<div class="{html.escape(classes)}">'
        f"{eyebrow_markup}"
        f'<div class="console-card-title">{html.escape(str(title))} {status_markup}</div>'
        f"{body_markup}{meta_markup}{content_html}"
        "</div>"
    )


def render_action_card(
    title: str,
    body: str,
    *,
    key_prefix: str,
    action_label: str = "Открыть",
    on_click: Any | None = None,
    args: tuple[Any, ...] = (),
    href: str = "",
    eyebrow: str = "",
    meta: str = "",
    status: str = "READY",
    disabled: bool = False,
    disabled_reason: str = "",
) -> bool:
    if not disabled and on_click is None and not href:
        raise ValueError("enabled action card requires on_click or href")
    card_status = "BLOCKED" if disabled else status
    card_class = "disabled-target-card" if disabled else "internal-action-card clickable-card"
    render_html(
        render_card(
            title,
            body,
            eyebrow=eyebrow,
            meta=meta,
            status=card_status,
            extra_class=card_class,
        )
    )
    clicked = render_action_button(
        action_label,
        key=safe_widget_key("action_card", key_prefix, title, action_label),
        on_click=on_click,
        args=args,
        href=href,
        disabled=disabled,
        disabled_reason=disabled_reason,
        help_text=meta,
    )
    if disabled and disabled_reason:
        st.caption(disabled_reason)
    return clicked


def render_empty_state(
    title: str,
    body: str,
    *,
    eyebrow: str = "Empty state",
    status: str = "NEEDS REVIEW",
    action: str = "",
) -> str:
    action_markup = ""
    if action:
        action_markup = f'<div class="console-card-meta">Дальше: {html.escape(str(action))}</div>'
    return render_card(
        title,
        body,
        eyebrow=eyebrow,
        status=status,
        extra_class="ui-state-card empty-state-card",
        content_html=action_markup,
    )


def render_warning_state(title: str, body: str, *, reason: str = "") -> str:
    content_html = f'<div class="console-card-meta">{html.escape(str(reason))}</div>' if reason else ""
    return render_card(
        title,
        body,
        eyebrow="Warning",
        status="NEEDS REVIEW",
        extra_class="ui-state-card warning-state-card",
        content_html=content_html,
    )


