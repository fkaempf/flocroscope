"""Tests for the shared logging configuration helper."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from virtual_reality.logging_config import setup_logging


@pytest.fixture(autouse=True)
def _reset_logging():
    """Reset the virtual_reality logger state between tests."""
    pkg_logger = logging.getLogger("virtual_reality")
    original_level = pkg_logger.level
    original_handlers = list(pkg_logger.handlers)
    yield
    pkg_logger.setLevel(original_level)
    # Remove any handlers added during the test
    for handler in pkg_logger.handlers:
        if handler not in original_handlers:
            pkg_logger.removeHandler(handler)
            handler.close()


class TestSetupLogging:
    """Tests for setup_logging()."""

    def test_sets_package_logger_level_info(self):
        """Default call sets virtual_reality logger to INFO."""
        setup_logging(level="INFO")
        pkg_logger = logging.getLogger("virtual_reality")
        assert pkg_logger.level == logging.INFO

    def test_sets_package_logger_level_debug(self):
        """Passing DEBUG sets the logger to DEBUG."""
        setup_logging(level="DEBUG")
        pkg_logger = logging.getLogger("virtual_reality")
        assert pkg_logger.level == logging.DEBUG

    def test_sets_package_logger_level_warning(self):
        """Passing WARNING sets the logger to WARNING."""
        setup_logging(level="WARNING")
        pkg_logger = logging.getLogger("virtual_reality")
        assert pkg_logger.level == logging.WARNING

    def test_sets_package_logger_level_error(self):
        """Passing ERROR sets the logger to ERROR."""
        setup_logging(level="ERROR")
        pkg_logger = logging.getLogger("virtual_reality")
        assert pkg_logger.level == logging.ERROR

    def test_case_insensitive_level(self):
        """Level string is case-insensitive."""
        setup_logging(level="debug")
        pkg_logger = logging.getLogger("virtual_reality")
        assert pkg_logger.level == logging.DEBUG

    def test_file_handler_added(self, tmp_path: Path):
        """When log_file is given, a FileHandler is attached."""
        log_path = str(tmp_path / "test.log")
        setup_logging(level="INFO", log_file=log_path)
        pkg_logger = logging.getLogger("virtual_reality")

        file_handlers = [
            h for h in pkg_logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) >= 1

        # Verify the handler points to the right file
        assert any(
            h.baseFilename == os.path.abspath(log_path)
            for h in file_handlers
        )

    def test_file_handler_writes(self, tmp_path: Path):
        """Messages are written to the log file."""
        log_path = tmp_path / "test.log"
        setup_logging(level="DEBUG", log_file=str(log_path))

        test_logger = logging.getLogger("virtual_reality.test_write")
        test_logger.info("hello from test")

        # Flush handlers
        for h in logging.getLogger("virtual_reality").handlers:
            h.flush()

        content = log_path.read_text()
        assert "hello from test" in content

    def test_no_file_handler_by_default(self):
        """Without log_file, no FileHandler is added."""
        pkg_logger = logging.getLogger("virtual_reality")
        before = len([
            h for h in pkg_logger.handlers
            if isinstance(h, logging.FileHandler)
        ])
        setup_logging(level="INFO")
        after = len([
            h for h in pkg_logger.handlers
            if isinstance(h, logging.FileHandler)
        ])
        assert after == before

    def test_idempotent_level_update(self):
        """Calling setup_logging twice updates the level."""
        setup_logging(level="DEBUG")
        pkg_logger = logging.getLogger("virtual_reality")
        assert pkg_logger.level == logging.DEBUG

        setup_logging(level="WARNING")
        assert pkg_logger.level == logging.WARNING
