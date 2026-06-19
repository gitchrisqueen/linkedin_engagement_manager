"""Unit tests for the structured logger module."""

import logging
import os
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_logger_module():
    """Re-import logger in isolation so module-level setup reruns cleanly."""
    import importlib
    import cqc_lem.utilities.logger as mod
    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# PostHogHandler
# ---------------------------------------------------------------------------

class TestPostHogHandler:
    def test_emit_sends_log_event_to_posthog(self):
        from cqc_lem.utilities.logger import PostHogHandler

        handler = PostHogHandler(level=logging.DEBUG)

        record = logging.LogRecord(
            name="cqc-lem", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="Something failed", args=(), exc_info=None,
        )

        with patch("posthog.capture") as mock_capture, \
             patch("posthog.disabled", False):
            handler.emit(record)

        mock_capture.assert_called_once()
        _, kwargs = mock_capture.call_args
        assert kwargs["event"] == "log_event"
        props = kwargs["properties"]
        assert props["level"] == "error"
        assert props["message"] == "Something failed"
        assert props["lineno"] == 1

    def test_emit_skips_when_posthog_disabled(self):
        from cqc_lem.utilities.logger import PostHogHandler

        handler = PostHogHandler(level=logging.DEBUG)
        record = logging.LogRecord(
            name="cqc-lem", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="Failure", args=(), exc_info=None,
        )

        with patch("posthog.disabled", True), patch("posthog.capture") as mock_capture:
            handler.emit(record)

        mock_capture.assert_not_called()

    def test_emit_includes_user_id_as_distinct_id(self):
        from cqc_lem.utilities.logger import PostHogHandler

        handler = PostHogHandler(level=logging.DEBUG)
        record = logging.LogRecord(
            name="cqc-lem", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="Error", args=(), exc_info=None,
        )
        record.user_id = 42

        with patch("posthog.capture") as mock_capture, \
             patch("posthog.disabled", False):
            handler.emit(record)

        _, kwargs = mock_capture.call_args
        assert kwargs["distinct_id"] == "42"
        assert kwargs["properties"]["user_id"] == 42

    def test_emit_captures_exc_info_fields(self):
        from cqc_lem.utilities.logger import PostHogHandler

        handler = PostHogHandler(level=logging.DEBUG)

        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="cqc-lem", level=logging.ERROR, pathname="test.py",
            lineno=5, msg="Caught exception", args=(), exc_info=exc_info,
        )

        with patch("posthog.capture") as mock_capture, \
             patch("posthog.disabled", False):
            handler.emit(record)

        props = mock_capture.call_args[1]["properties"]
        assert props["error_type"] == "ValueError"
        assert "boom" in props["error_message"]
        assert "ValueError" in props["stack_trace"]

    def test_emit_uses_system_distinct_id_when_no_user_id(self):
        from cqc_lem.utilities.logger import PostHogHandler

        handler = PostHogHandler(level=logging.DEBUG)
        record = logging.LogRecord(
            name="cqc-lem", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="No user", args=(), exc_info=None,
        )

        with patch("posthog.capture") as mock_capture, \
             patch("posthog.disabled", False):
            handler.emit(record)

        assert mock_capture.call_args[1]["distinct_id"] == "system"

    def test_emit_handles_posthog_error_gracefully(self):
        from cqc_lem.utilities.logger import PostHogHandler

        handler = PostHogHandler(level=logging.DEBUG)
        record = logging.LogRecord(
            name="cqc-lem", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="Msg", args=(), exc_info=None,
        )

        with patch("posthog.disabled", False), \
             patch("posthog.capture", side_effect=RuntimeError("network error")):
            # Should not raise — handleError is called instead
            handler.emit(record)


# ---------------------------------------------------------------------------
# log_debug / log_info / log_warning
# ---------------------------------------------------------------------------

class TestLogLevelFunctions:
    def test_log_debug_calls_logger_debug(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "debug") as mock_debug:
            mod.log_debug("debug msg", user_id=7)

        mock_debug.assert_called_once()
        args, kwargs = mock_debug.call_args
        assert args[0] == "debug msg"
        assert kwargs["extra"]["user_id"] == 7

    def test_log_info_calls_logger_info(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "info") as mock_info:
            mod.log_info("info msg", task_name="my_task")

        mock_info.assert_called_once()
        assert mock_info.call_args[1]["extra"]["task_name"] == "my_task"

    def test_log_warning_calls_logger_warning(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "warning") as mock_warn:
            mod.log_warning("warn msg", post_id=99)

        mock_warn.assert_called_once()
        assert mock_warn.call_args[1]["extra"]["post_id"] == 99

    def test_extra_filters_out_none_values(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "info") as mock_info:
            mod.log_info("msg", user_id=None, task_name="t")

        extra = mock_info.call_args[1]["extra"]
        assert "user_id" not in extra
        assert extra["task_name"] == "t"


# ---------------------------------------------------------------------------
# log_error / log_critical
# ---------------------------------------------------------------------------

class TestLogError:
    def test_log_error_without_exc(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "error") as mock_err:
            mod.log_error("something broke", user_id=5)

        mock_err.assert_called_once_with("something broke", extra={"user_id": 5})

    def test_log_error_with_exc_passes_exc_info(self):
        from cqc_lem.utilities import logger as mod

        exc = ValueError("test error")
        with patch.object(mod.logger, "error") as mock_err:
            mod.log_error("error with exc", exc=exc, user_id=3)

        _, kwargs = mock_err.call_args
        assert kwargs["exc_info"] is exc
        assert kwargs["extra"]["user_id"] == 3

    def test_log_critical_with_exc(self):
        from cqc_lem.utilities import logger as mod

        exc = RuntimeError("fatal")
        with patch.object(mod.logger, "critical") as mock_crit:
            mod.log_critical("critical error", exc=exc)

        assert mock_crit.call_args[1]["exc_info"] is exc

    def test_log_critical_without_exc(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "critical") as mock_crit:
            mod.log_critical("critical msg", task_name="fatal_task")

        mock_crit.assert_called_once_with("critical msg", extra={"task_name": "fatal_task"})


# ---------------------------------------------------------------------------
# myprint (backward-compat shim)
# ---------------------------------------------------------------------------

class TestMyprint:
    def test_myprint_routes_to_info_by_default(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "info") as mock_info:
            mod.myprint("hello")

        mock_info.assert_called_once_with("hello")

    def test_myprint_debug_true_routes_to_debug(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "debug") as mock_debug:
            mod.myprint("verbose detail", debug=True)

        mock_debug.assert_called_once_with("verbose detail")

    def test_myprint_debug_false_does_not_call_debug(self):
        from cqc_lem.utilities import logger as mod

        with patch.object(mod.logger, "debug") as mock_debug, \
             patch.object(mod.logger, "info"):
            mod.myprint("normal message")

        mock_debug.assert_not_called()


# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------

class TestLoggerConfiguration:
    def test_logger_has_file_handler(self):
        from cqc_lem.utilities import logger as mod

        handler_types = [type(h).__name__ for h in mod.logger.handlers]
        assert "RotatingFileHandler" in handler_types

    def test_logger_has_posthog_handler(self):
        from cqc_lem.utilities import logger as mod

        handler_types = [type(h).__name__ for h in mod.logger.handlers]
        assert "PostHogHandler" in handler_types

    def test_logger_has_stream_handler(self):
        from cqc_lem.utilities import logger as mod

        handler_types = [type(h).__name__ for h in mod.logger.handlers]
        assert "StreamHandler" in handler_types

    def test_logger_does_not_propagate(self):
        from cqc_lem.utilities import logger as mod

        assert mod.logger.propagate is False

    def test_posthog_handler_level_defaults_to_error(self):
        from cqc_lem.utilities import logger as mod

        ph_handlers = [h for h in mod.logger.handlers if type(h).__name__ == "PostHogHandler"]
        assert ph_handlers, "No PostHogHandler found"
        assert ph_handlers[0].level == logging.ERROR
