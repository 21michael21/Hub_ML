"""Configuration loading from .env and optional YAML."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .errors import ConfigError
from .models import AppConfig


DEFAULT_LISTS = [
    "Inbox",
    "Backlog",
    "Next",
    "Today",
    "In Progress",
    "Waiting",
    "Review",
    "Done",
]

DEFAULT_PROJECTS = [
    "CRM",
    "Landing",
    "Bot",
    "Database",
    "Docs",
    "Learning",
    "Personal",
    "Finance",
]

DEFAULT_PRIORITIES = ["P1", "P2", "P3"]


def _as_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} must contain a YAML object.")
    return data


def load_config(
    project_root: Path,
    config_path: str | None = None,
    mock_override: bool | None = None,
) -> AppConfig:
    """Load runtime config.

    Precedence:
    1. Explicit CLI values.
    2. Environment variables from shell or .env.
    3. YAML config.
    4. Built-in defaults.
    """

    load_dotenv(project_root / ".env")
    yaml_path = Path(config_path) if config_path else project_root / "config.yaml"
    data = _load_yaml(yaml_path)

    trello = data.get("trello") or {}
    calendar = data.get("calendar") or {}

    timezone = (
        os.getenv("DEFAULT_TIMEZONE")
        or data.get("timezone")
        or "Europe/Stockholm"
    )
    mock = _as_bool(os.getenv("TASKCTL_MOCK"))
    if mock_override is not None:
        mock = mock_override

    return AppConfig(
        timezone=str(timezone),
        trello_api_key=os.getenv("TRELLO_API_KEY") or None,
        trello_token=os.getenv("TRELLO_TOKEN") or None,
        trello_board_id=os.getenv("TRELLO_BOARD_ID") or None,
        google_client_secret_file=os.getenv("GOOGLE_CLIENT_SECRET_FILE") or None,
        google_token_file=os.getenv("GOOGLE_TOKEN_FILE") or "token.json",
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID")
        or str(calendar.get("calendar_id") or "primary"),
        trello_board_name=str(trello.get("board_name") or "Command Center"),
        trello_lists=list(trello.get("lists") or DEFAULT_LISTS),
        projects=list(data.get("projects") or DEFAULT_PROJECTS),
        priorities=list(data.get("priorities") or DEFAULT_PRIORITIES),
        calendar_name=str(calendar.get("calendar_name") or "Task Command Center"),
        default_reminders=list(calendar.get("default_reminders") or [30, 5]),
        default_duration_minutes=int(calendar.get("default_duration_minutes") or 120),
        mock=mock,
    )


def require_real_credentials(config: AppConfig, trello: bool = False, google: bool = False) -> None:
    missing: list[str] = []
    if trello:
        if not config.trello_api_key:
            missing.append("TRELLO_API_KEY")
        if not config.trello_token:
            missing.append("TRELLO_TOKEN")
        if not config.trello_board_id:
            missing.append("TRELLO_BOARD_ID")
    if google:
        if not config.google_client_secret_file:
            missing.append("GOOGLE_CLIENT_SECRET_FILE")
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(
            f"Missing required credentials: {joined}. "
            "Fill .env or run with TASKCTL_MOCK=1 for local testing."
        )
