"""Shared logging setup for the virtual_reality package.

Provides a single :func:`setup_logging` helper that configures the
root ``virtual_reality`` logger with a consistent format, level, and
optional file output.  All CLI entry points should call this early in
their ``main()`` function.
"""

from __future__ import annotations

import logging


_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """Configure logging for the virtual_reality package.

    Sets up ``logging.basicConfig`` with a standard format and
    configures the ``virtual_reality`` package logger to the
    requested level.  An optional file handler can be added for
    persistent log output.

    This function is idempotent: calling it multiple times updates
    the level and (if *log_file* changes) adds additional file
    handlers, but does not duplicate the basic configuration.

    Args:
        level: Logging level name (``DEBUG``, ``INFO``,
            ``WARNING``, ``ERROR``, ``CRITICAL``).
        log_file: Optional path to a log file.  If provided, a
            :class:`~logging.FileHandler` is attached to the
            ``virtual_reality`` logger.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format=_LOG_FORMAT,
        level=numeric_level,
    )

    pkg_logger = logging.getLogger("virtual_reality")
    pkg_logger.setLevel(numeric_level)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        pkg_logger.addHandler(file_handler)
