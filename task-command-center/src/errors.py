"""Custom errors for task-command-center."""


class TaskCtlError(Exception):
    """Base class for user-facing CLI errors."""


class ConfigError(TaskCtlError):
    """Raised when configuration or secrets are missing."""


class TrelloError(TaskCtlError):
    """Raised for Trello API and lookup failures."""


class CalendarError(TaskCtlError):
    """Raised for Google Calendar API and lookup failures."""


class NotFoundError(TaskCtlError):
    """Raised when a requested object cannot be found."""


class AmbiguousMatchError(TaskCtlError):
    """Raised when a text search matches multiple objects."""
