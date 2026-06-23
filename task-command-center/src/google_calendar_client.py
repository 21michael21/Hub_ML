"""Google Calendar client with a local mock backend."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import require_real_credentials
from .errors import CalendarError, NotFoundError
from .models import AppConfig, CalendarEventInput


SCOPES = ["https://www.googleapis.com/auth/calendar"]
READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


class GoogleCalendarClient:
    def __init__(self, config: AppConfig, project_root: Path) -> None:
        self.config = config
        self.project_root = project_root
        self.mock_path = project_root / ".taskctl_mock" / "calendar.json"
        self.service: Any = None
        if not self.config.mock:
            require_real_credentials(config, google=True)

    def authenticate(self) -> Any:
        if self.config.mock:
            return None

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise CalendarError(
                "Google Calendar libraries are not installed. Run: pip install -r requirements.txt"
            ) from exc

        creds = None
        token_path = self.token_path()
        self.validate_setup()
        self._reject_readonly_token(token_path)
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            except ValueError as exc:
                raise CalendarError(
                    f"Cannot read Google token file: {token_path}. "
                    "Delete token.json and run calendar-test again."
                ) from exc
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as exc:
                    raise CalendarError(_google_auth_error_message(exc)) from exc
            else:
                secret_path = self.client_secret_path()
                flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
                try:
                    creds = flow.run_local_server(port=0)
                except Exception as exc:
                    raise CalendarError(_google_auth_error_message(exc)) from exc
            token_path.write_text(creds.to_json(), encoding="utf-8")
        self.service = build("calendar", "v3", credentials=creds)
        return self.service

    def create_event(self, event_input: CalendarEventInput) -> dict[str, Any]:
        body = self.build_event_body(event_input)
        if self.config.mock:
            store = self._load_store()
            event = {
                "id": f"event-{len(store['events']) + 1}",
                **body,
                "htmlLink": f"mock://calendar/events/{len(store['events']) + 1}",
                "created": _now(),
            }
            store["events"].append(event)
            self._save_store(store)
            return event

        service = self.authenticate()
        try:
            return (
                service.events()
                .insert(calendarId=self.config.google_calendar_id, body=body)
                .execute()
            )
        except Exception as exc:  # googleapiclient raises several transport exceptions.
            raise CalendarError(_google_api_error_message(exc, "create_event")) from exc

    def create_reminder_event(
        self,
        title: str,
        at: datetime,
        duration_minutes: int,
        reminder_minutes: int | None,
    ) -> dict[str, Any]:
        return self.create_event(
            CalendarEventInput(
                title=title,
                start=at,
                end=at + timedelta(minutes=duration_minutes),
                reminder_minutes=reminder_minutes,
                description="Reminder created by taskctl.",
            )
        )

    def list_today_events(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        if self.config.mock:
            return [
                event
                for event in self._load_store()["events"]
                if _event_start(event) and start <= _event_start(event) < end
            ]

        service = self.authenticate()
        try:
            response = (
                service.events()
                .list(
                    calendarId=self.config.google_calendar_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return list(response.get("items", []))
        except Exception as exc:
            raise CalendarError(_google_api_error_message(exc, "list_today_events")) from exc

    def find_event_by_title(self, title: str) -> dict[str, Any]:
        if self.config.mock:
            events = self._load_store()["events"]
        else:
            service = self.authenticate()
            try:
                response = (
                    service.events()
                    .list(
                        calendarId=self.config.google_calendar_id,
                        q=title,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
                events = list(response.get("items", []))
            except Exception as exc:
                raise CalendarError(_google_api_error_message(exc, "find_event_by_title")) from exc

        query = title.strip().lower()
        exact = [event for event in events if str(event.get("summary", "")).lower() == query]
        if len(exact) == 1:
            return exact[0]
        partial = [event for event in events if query in str(event.get("summary", "")).lower()]
        if len(partial) == 1:
            return partial[0]
        if not exact and not partial:
            raise NotFoundError(f"Cannot find calendar event titled '{title}'.")
        matches = ", ".join(str(event.get("summary")) for event in [*exact, *partial])
        raise CalendarError(f"'{title}' matches multiple events: {matches}.")

    def delete_event_by_title(self, title: str) -> dict[str, Any]:
        event = self.find_event_by_title(title)
        event_id = str(event["id"])
        if self.config.mock:
            store = self._load_store()
            store["events"] = [item for item in store["events"] if item.get("id") != event_id]
            self._save_store(store)
            return event

        service = self.authenticate()
        try:
            service.events().delete(
                calendarId=self.config.google_calendar_id,
                eventId=event_id,
            ).execute()
        except Exception as exc:
            raise CalendarError(_google_api_error_message(exc, "delete_event_by_title")) from exc
        return event

    def build_event_body(self, event_input: CalendarEventInput) -> dict[str, Any]:
        reminders = (
            [event_input.reminder_minutes]
            if event_input.reminder_minutes is not None
            else self.config.default_reminders
        )
        return {
            "summary": event_input.title,
            "description": event_input.description,
            "start": {
                "dateTime": event_input.start.isoformat(timespec="seconds"),
                "timeZone": self.config.timezone,
            },
            "end": {
                "dateTime": event_input.end.isoformat(timespec="seconds"),
                "timeZone": self.config.timezone,
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": minutes}
                    for minutes in reminders
                    if minutes is not None
                ],
            },
        }

    def client_secret_path(self) -> Path:
        secret_path = Path(self.config.google_client_secret_file or "")
        if not secret_path.is_absolute():
            secret_path = self.project_root / secret_path
        return secret_path

    def token_path(self) -> Path:
        token_path = Path(self.config.google_token_file)
        if not token_path.is_absolute():
            token_path = self.project_root / token_path
        return token_path

    def validate_setup(self) -> None:
        if not self.config.google_calendar_id:
            raise CalendarError("GOOGLE_CALENDAR_ID is empty. Set it in .env.")
        if not self.config.timezone:
            raise CalendarError("DEFAULT_TIMEZONE is empty. Set it in .env.")
        secret_path = self.client_secret_path()
        if not secret_path.exists():
            raise CalendarError(
                f"Google client secret file not found: {secret_path}. "
                "Download OAuth Desktop credentials from Google Cloud, save it as "
                "client_secret.json in the project folder, and keep "
                "GOOGLE_CLIENT_SECRET_FILE=client_secret.json in .env."
            )

    def _reject_readonly_token(self, token_path: Path) -> None:
        if not token_path.exists():
            return
        try:
            with token_path.open("r", encoding="utf-8") as handle:
                token_data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise CalendarError(
                f"Cannot read Google token file: {token_path}. "
                "Delete token.json and run calendar-test again."
            ) from exc

        scopes = token_data.get("scopes") or token_data.get("scope") or []
        if isinstance(scopes, str):
            scopes = scopes.split()
        scope_set = set(scopes)
        if READONLY_SCOPE in scope_set and SCOPES[0] not in scope_set:
            raise CalendarError(
                "token.json was created with Google Calendar readonly scope. "
                "Delete token.json and run `python taskctl.py calendar-test` again "
                "so OAuth can request https://www.googleapis.com/auth/calendar."
            )

    def _load_store(self) -> dict[str, Any]:
        if self.mock_path.exists():
            with self.mock_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        store = {
            "calendar": {
                "id": self.config.google_calendar_id,
                "name": self.config.calendar_name,
            },
            "events": [],
        }
        self._save_store(store)
        return store

    def _save_store(self, store: dict[str, Any]) -> None:
        self.mock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.mock_path.open("w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)


def _event_start(event: dict[str, Any]) -> datetime | None:
    raw = (event.get("start") or {}).get("dateTime")
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _google_auth_error_message(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "access_denied" in lowered or "not completed the google verification process" in lowered:
        return (
            "Google OAuth denied access. If the app is in Testing mode, add your "
            "Google account to OAuth consent screen Test users, then run calendar-test again."
        )
    if "invalid_grant" in lowered:
        return "Google OAuth token is invalid or expired. Delete token.json and run calendar-test again."
    return f"Google OAuth failed: {text}"


def _google_api_error_message(exc: Exception, operation: str) -> str:
    status = getattr(getattr(exc, "resp", None), "status", None)
    content = getattr(exc, "content", b"")
    if isinstance(content, bytes):
        content_text = content.decode("utf-8", errors="replace")
    else:
        content_text = str(content)
    lowered = content_text.lower()

    if status == 403 and ("insufficient" in lowered or "forbidden" in lowered):
        return (
            f"Google Calendar {operation} failed: no permission to create or edit events. "
            "Delete token.json and re-run calendar-test to grant full Calendar scope."
        )
    if status == 403 and ("accessnotconfigured" in lowered or "api has not been used" in lowered):
        return (
            f"Google Calendar {operation} failed: Google Calendar API is not enabled "
            "for this Google Cloud project. Enable the API, then run calendar-test again."
        )
    if status == 404:
        return (
            f"Google Calendar {operation} failed: calendar_id was not found. "
            "Check GOOGLE_CALENDAR_ID in .env or use primary."
        )
    if status == 401:
        return (
            f"Google Calendar {operation} failed: OAuth token is invalid. "
            "Delete token.json and run calendar-test again."
        )
    return f"Google Calendar {operation} failed: {exc}"
