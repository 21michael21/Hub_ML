#!/usr/bin/env python3
"""CLI entrypoint for Task Command Center."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import load_config
from src.date_parser import add_minutes, parse_date, parse_datetime
from src.errors import TaskCtlError
from src.formatter import format_card, format_cards, format_event
from src.google_calendar_client import GoogleCalendarClient
from src.models import CalendarEventInput, TaskCardInput
from src.trello_client import TrelloClient


PROJECT_ROOT = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--config", default=argparse.SUPPRESS, help="Path to config.yaml")
    shared.add_argument(
        "--mock",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Use local mock storage instead of real APIs",
    )

    parser = argparse.ArgumentParser(
        prog="taskctl",
        description="Task Command Center CLI for Trello and Google Calendar.",
        parents=[shared],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_cmd = subparsers.add_parser("new", parents=[shared], help="Create a Trello card")
    new_cmd.add_argument("--title", required=True)
    new_cmd.add_argument("--project", choices=None)
    new_cmd.add_argument("--priority", choices=None)
    new_cmd.add_argument("--list", default="Inbox", dest="list_name")
    new_cmd.add_argument("--due")
    new_cmd.add_argument("--description", default="")
    new_cmd.add_argument("--criteria", action="append", default=[])
    new_cmd.add_argument("--calendar-start")
    new_cmd.add_argument("--calendar-end")
    new_cmd.add_argument("--reminder", type=int)
    new_cmd.set_defaults(func=cmd_new)

    list_cmd = subparsers.add_parser("list", parents=[shared], help="List Trello cards")
    list_cmd.add_argument("--list", dest="list_name")
    list_cmd.add_argument("--project")
    list_cmd.add_argument("--priority")
    list_cmd.set_defaults(func=cmd_list)

    move_cmd = subparsers.add_parser("move", parents=[shared], help="Move a card")
    move_cmd.add_argument("--card", required=True)
    move_cmd.add_argument("--to", required=True)
    move_cmd.set_defaults(func=cmd_move)

    done_cmd = subparsers.add_parser("done", parents=[shared], help="Move card to Done")
    done_cmd.add_argument("--card", required=True)
    done_cmd.add_argument("--summary", required=True)
    done_cmd.set_defaults(func=cmd_done)

    delete_cmd = subparsers.add_parser(
        "delete",
        parents=[shared],
        help="Permanently delete a Trello card; requires --yes",
    )
    delete_cmd.add_argument("--card", required=True)
    delete_cmd.add_argument(
        "--yes",
        action="store_true",
        help="Confirm permanent deletion",
    )
    delete_cmd.set_defaults(func=cmd_delete)

    calendar_cmd = subparsers.add_parser(
        "calendar",
        parents=[shared],
        help="Create a Google Calendar event",
    )
    calendar_cmd.add_argument("--title", required=True)
    calendar_cmd.add_argument("--start", required=True)
    calendar_cmd.add_argument("--end", required=True)
    calendar_cmd.add_argument("--reminder", type=int)
    calendar_cmd.add_argument("--description", default="")
    calendar_cmd.set_defaults(func=cmd_calendar)

    calendar_test_cmd = subparsers.add_parser(
        "calendar-test",
        parents=[shared],
        help="Run Google Calendar OAuth and create a short test event",
    )
    calendar_test_cmd.set_defaults(func=cmd_calendar_test)

    remind_cmd = subparsers.add_parser(
        "remind",
        parents=[shared],
        help="Create a short reminder event",
    )
    remind_cmd.add_argument("--title", required=True)
    remind_cmd.add_argument("--at", required=True)
    remind_cmd.add_argument("--duration", type=int, default=15)
    remind_cmd.add_argument("--reminder", type=int, default=30)
    remind_cmd.set_defaults(func=cmd_remind)

    comment_cmd = subparsers.add_parser("comment", parents=[shared], help="Add a Trello comment")
    comment_cmd.add_argument("--card", required=True)
    comment_cmd.add_argument("--text", required=True)
    comment_cmd.set_defaults(func=cmd_comment)

    link_cmd = subparsers.add_parser("link", parents=[shared], help="Add a link to a Trello card")
    link_cmd.add_argument("--card", required=True)
    link_cmd.add_argument("--url", required=True)
    link_cmd.set_defaults(func=cmd_link)

    return parser


def cmd_new(args: argparse.Namespace) -> int:
    config = _config(args)
    _validate_choice(args.list_name, config.trello_lists, "list")
    if args.project:
        _validate_choice(args.project, config.projects, "project")
    if args.priority:
        _validate_choice(args.priority, config.priorities, "priority")

    calendar: GoogleCalendarClient | None = None
    calendar_event_input: CalendarEventInput | None = None
    if args.calendar_start or args.calendar_end:
        if not args.calendar_start or not args.calendar_end:
            raise TaskCtlError("--calendar-start and --calendar-end must be used together.")
        calendar = GoogleCalendarClient(config, PROJECT_ROOT)
        calendar.validate_setup()
        calendar_event_input = CalendarEventInput(
            title=args.title,
            start=parse_datetime(args.calendar_start, config.timezone),
            end=parse_datetime(args.calendar_end, config.timezone),
            reminder_minutes=args.reminder,
            description="",
        )

    trello = TrelloClient(config, PROJECT_ROOT)
    card = trello.create_card(
        TaskCardInput(
            title=args.title,
            project=args.project,
            priority=args.priority,
            list_name=args.list_name,
            due=parse_date(args.due),
            description=args.description,
            criteria=args.criteria,
        )
    )
    print("Created Trello card:")
    print(format_card(card))

    if calendar and calendar_event_input:
        calendar_event_input = CalendarEventInput(
            title=calendar_event_input.title,
            start=calendar_event_input.start,
            end=calendar_event_input.end,
            reminder_minutes=calendar_event_input.reminder_minutes,
            description=f"Trello card: {card.get('shortUrl') or card.get('url') or card.get('name')}",
        )
        event = calendar.create_event(calendar_event_input)
        print("Created calendar event:")
        print(format_event(event))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    config = _config(args)
    if args.list_name:
        _validate_choice(args.list_name, config.trello_lists, "list")
    if args.project:
        _validate_choice(args.project, config.projects, "project")
    if args.priority:
        _validate_choice(args.priority, config.priorities, "priority")

    trello = TrelloClient(config, PROJECT_ROOT)
    cards = trello.list_cards(
        list_name=args.list_name,
        project=args.project,
        priority=args.priority,
    )
    print(format_cards(cards))
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    config = _config(args)
    _validate_choice(args.to, config.trello_lists, "list")
    trello = TrelloClient(config, PROJECT_ROOT)
    card = trello.find_card_by_name(args.card)
    moved = trello.move_card(card, args.to)
    print("Moved card:")
    print(format_card(moved))
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    config = _config(args)
    trello = TrelloClient(config, PROJECT_ROOT)
    card = trello.find_card_by_name(args.card)
    trello.add_comment(card, f"Done summary: {args.summary}")
    moved = trello.move_card(card, "Done")
    print("Completed card:")
    print(format_card(moved))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    if not args.yes:
        raise TaskCtlError("Permanent delete requires --yes.")
    config = _config(args)
    trello = TrelloClient(config, PROJECT_ROOT)
    card = trello.find_card_by_name(args.card)
    trello.delete_card(card)
    print(f"Deleted card: {card.get('name')}")
    return 0


def cmd_calendar(args: argparse.Namespace) -> int:
    config = _config(args)
    calendar = GoogleCalendarClient(config, PROJECT_ROOT)
    event = calendar.create_event(
        CalendarEventInput(
            title=args.title,
            start=parse_datetime(args.start, config.timezone),
            end=parse_datetime(args.end, config.timezone),
            reminder_minutes=args.reminder,
            description=args.description,
        )
    )
    print("Created calendar event:")
    print(format_event(event))
    return 0


def cmd_calendar_test(args: argparse.Namespace) -> int:
    config = _config(args)
    calendar = GoogleCalendarClient(config, PROJECT_ROOT)
    calendar.validate_setup()
    now = datetime.now(ZoneInfo(config.timezone)).replace(second=0, microsecond=0)
    start = now + timedelta(minutes=10)
    end = start + timedelta(minutes=15)
    event = calendar.create_event(
        CalendarEventInput(
            title="TASKCTL TEST - Google Calendar calendar-test",
            start=start,
            end=end,
            reminder_minutes=5,
            description="Created by taskctl calendar-test. Delete manually after verification.",
        )
    )
    print("Google Calendar test event created:")
    print(f"title: {event.get('summary')}")
    print(f"start: {(event.get('start') or {}).get('dateTime')}")
    print(f"end: {(event.get('end') or {}).get('dateTime')}")
    print(f"event_id: {event.get('id')}")
    print("The event was not deleted automatically.")
    return 0


def cmd_remind(args: argparse.Namespace) -> int:
    config = _config(args)
    calendar = GoogleCalendarClient(config, PROJECT_ROOT)
    event = calendar.create_reminder_event(
        title=args.title,
        at=parse_datetime(args.at, config.timezone),
        duration_minutes=args.duration,
        reminder_minutes=args.reminder,
    )
    print("Created reminder event:")
    print(format_event(event))
    return 0


def cmd_comment(args: argparse.Namespace) -> int:
    config = _config(args)
    trello = TrelloClient(config, PROJECT_ROOT)
    card = trello.find_card_by_name(args.card)
    trello.add_comment(card, args.text)
    print(f"Added comment to: {card.get('name')}")
    return 0


def cmd_link(args: argparse.Namespace) -> int:
    config = _config(args)
    trello = TrelloClient(config, PROJECT_ROOT)
    card = trello.find_card_by_name(args.card)
    current_desc = str(card.get("desc") or "")
    updated_desc = current_desc.rstrip() + f"\n\nLinks:\n- {args.url}\n"
    updated = trello.update_card(card, desc=updated_desc)
    trello.add_comment(updated, f"Linked: {args.url}")
    print("Added link to card:")
    print(format_card(updated))
    return 0


def _config(args: argparse.Namespace):
    mock_value = getattr(args, "mock", None)
    return load_config(
        PROJECT_ROOT,
        getattr(args, "config", None),
        mock_override=True if mock_value else None,
    )


def _validate_choice(value: str, allowed: list[str], kind: str) -> None:
    if value not in allowed:
        joined = ", ".join(allowed)
        raise TaskCtlError(f"Unknown {kind} '{value}'. Allowed values: {joined}.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except TaskCtlError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
