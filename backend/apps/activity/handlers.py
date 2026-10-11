import logging
import traceback

MAX_TRACEBACK = 5000


class ActivityLogHandler(logging.Handler):
    """Writes server errors to the activity log (architecture 10)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from .log import log_event  # logging is configured before apps are loaded

            request = getattr(record, "request", None)
            details: dict[str, object] = {
                "message": record.getMessage(),
                "logger": record.name,
                "path": getattr(request, "path", None),
                "method": getattr(request, "method", None),
                "status": getattr(record, "status_code", None),
            }
            if record.exc_info:
                text = "".join(traceback.format_exception(*record.exc_info))
                details["traceback"] = text[-MAX_TRACEBACK:]
            log_event("error", "server_error", getattr(request, "user", None), **details)
        except Exception:
            self.handleError(record)
