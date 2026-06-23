"""Human-readable CLI output helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def format_card(card: dict[str, Any]) -> str:
    labels = ", ".join(_label_names(card)) or "-"
    list_name = card.get("listName") or card.get("list_name") or card.get("idList") or "-"
    due = card.get("due") or "-"
    status = "closed" if card.get("closed") else "open"
    url = card.get("shortUrl") or card.get("url")
    base = f"- {card.get('name')} [{status}] | list: {list_name} | labels: {labels} | due: {due}"
    if url:
        base += f" | {url}"
    return base


def format_cards(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return "No cards found."
    return "\n".join(format_card(card) for card in cards)


def format_event(event: dict[str, Any]) -> str:
    start = _event_dt(event.get("start"))
    end = _event_dt(event.get("end"))
    link = event.get("htmlLink")
    text = f"- {event.get('summary')} | {start} - {end}"
    if link:
        text += f" | {link}"
    return text


def _label_names(card: dict[str, Any]) -> list[str]:
    labels = card.get("labels") or card.get("labelNames") or []
    names: list[str] = []
    for label in labels:
        if isinstance(label, dict):
            names.append(str(label.get("name") or label.get("id") or ""))
        else:
            names.append(str(label))
    return [name for name in names if name]


def _event_dt(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("dateTime") or value.get("date") or "-")
    if isinstance(value, datetime):
        return value.isoformat(timespec="minutes")
    return str(value or "-")
