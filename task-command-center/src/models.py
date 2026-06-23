"""Typed data models used by the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class TaskCardInput:
    title: str
    project: str | None = None
    priority: str | None = None
    list_name: str = "Inbox"
    due: str | None = None
    description: str = ""
    criteria: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CalendarEventInput:
    title: str
    start: datetime
    end: datetime
    reminder_minutes: int | None = None
    description: str = ""


@dataclass(frozen=True)
class AppConfig:
    timezone: str
    trello_api_key: str | None
    trello_token: str | None
    trello_board_id: str | None
    google_client_secret_file: str | None
    google_token_file: str
    google_calendar_id: str
    trello_board_name: str
    trello_lists: list[str]
    projects: list[str]
    priorities: list[str]
    calendar_name: str
    default_reminders: list[int]
    default_duration_minutes: int
    mock: bool = False
