import logging
import os
import sys
import traceback
import datetime as DT
from logging.handlers import RotatingFileHandler
from typing import Optional

_LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
# PostHog receives records at this level and above (default: ERROR)
_POSTHOG_MIN_LEVEL = getattr(logging, os.getenv("POSTHOG_LOG_LEVEL", "ERROR").upper(), logging.ERROR)

_today = DT.date.today()
LOGGING_FILENAME = "logs/cqc_lem_" + _today.strftime("%Y_%m_%d") + ".log"
os.makedirs("logs", exist_ok=True)

# Structured extra keys forwarded to PostHog when present on a LogRecord
_POSTHOG_EXTRA_KEYS = (
    "user_id", "task_id", "task_name", "post_id", "action_type",
    "duration_ms", "ai_model", "api_provider", "http_status",
    "error_type", "error_message", "stack_trace",
)


class PostHogHandler(logging.Handler):
    """Forwards log records to PostHog as `log_event` captures.

    Structured context is attached via `extra=` on the log call.
    Exceptions are captured with their full traceback automatically.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            import posthog as _ph  # local import — avoids circular dep at module load

            if _ph.disabled:
                return

            props: dict = {
                "level": record.levelname.lower(),
                "module": record.module,
                "function": record.funcName,
                "filename": record.filename,
                "lineno": record.lineno,
                "message": record.getMessage(),
            }

            for key in _POSTHOG_EXTRA_KEYS:
                val = getattr(record, key, None)
                if val is not None:
                    props[key] = val

            if record.exc_info and record.exc_info[0] is not None:
                exc_cls, exc_val, exc_tb = record.exc_info
                props.setdefault("error_type", exc_cls.__name__)
                props.setdefault("error_message", str(exc_val))
                props.setdefault("stack_trace", "".join(traceback.format_exception(exc_cls, exc_val, exc_tb)))

            distinct_id = str(props.get("user_id") or "system")
            _ph.capture(distinct_id=distinct_id, event="log_event", properties=props)
        except Exception:
            self.handleError(record)


class _LevelFormatter(logging.Formatter):
    _fmt_debug = "[%(asctime)s %(filename)s->%(funcName)s():%(lineno)s] DEBUG: %(message)s"
    _fmt_info = "%(message)s"
    _fmt_warning = "WARNING [%(filename)s:%(lineno)s]: %(message)s"
    _fmt_error = "ERROR [%(filename)s->%(funcName)s():%(lineno)s]: %(message)s"
    _fmt_critical = "CRITICAL [%(filename)s->%(funcName)s():%(lineno)s]: %(message)s"

    _map = {
        logging.DEBUG: _fmt_debug,
        logging.INFO: _fmt_info,
        logging.WARNING: _fmt_warning,
        logging.ERROR: _fmt_error,
        logging.CRITICAL: _fmt_critical,
    }

    def format(self, record: logging.LogRecord) -> str:
        self._style._fmt = self._map.get(record.levelno, "%(levelname)s: %(message)s")
        return super().format(record)


# ── Build logger ─────────────────────────────────────────────────────────────

logger = logging.getLogger("cqc-lem")
logger.setLevel(_LOG_LEVEL)
logger.propagate = False  # don't double-log via root

_formatter = _LevelFormatter()

_file_handler = RotatingFileHandler(LOGGING_FILENAME, maxBytes=250_000_000, backupCount=10)
_file_handler.setFormatter(_formatter)
_file_handler.setLevel(_LOG_LEVEL)
logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_formatter)
_console_handler.setLevel(_LOG_LEVEL)
logger.addHandler(_console_handler)

_posthog_handler = PostHogHandler(level=_POSTHOG_MIN_LEVEL)
logger.addHandler(_posthog_handler)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _extra(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}


# ── Public API ────────────────────────────────────────────────────────────────

def myprint(message: str, debug: bool = False) -> None:
    """Backward-compatible shim. Prefer log_info / log_debug for new code."""
    if debug:
        logger.debug(message)
    else:
        logger.info(message)


def log_debug(message: str, **context) -> None:
    """Log at DEBUG level with optional structured context."""
    logger.debug(message, extra=_extra(**context))


def log_info(message: str, **context) -> None:
    """Log at INFO level with optional structured context."""
    logger.info(message, extra=_extra(**context))


def log_warning(message: str, **context) -> None:
    """Log at WARNING level with optional structured context."""
    logger.warning(message, extra=_extra(**context))


def log_error(
    message: str,
    exc: Optional[BaseException] = None,
    **context,
) -> None:
    """Log at ERROR level. Pass exc= to capture exception info and stack trace."""
    if exc is not None:
        logger.error(message, exc_info=exc, extra=_extra(**context))
    else:
        logger.error(message, extra=_extra(**context))


def log_critical(
    message: str,
    exc: Optional[BaseException] = None,
    **context,
) -> None:
    """Log at CRITICAL level. Pass exc= to capture exception info and stack trace."""
    if exc is not None:
        logger.critical(message, exc_info=exc, extra=_extra(**context))
    else:
        logger.critical(message, extra=_extra(**context))
