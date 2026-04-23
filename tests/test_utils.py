"""Tests for small utility helpers."""

import logging
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from parazettel_mcp.utils import format_note_for_display, parse_tags, setup_logging


def test_setup_logging_falls_back_to_info_and_stderr():
    """Unknown log levels should fall back to INFO and log to stderr."""
    with patch("parazettel_mcp.utils.logging.basicConfig") as basic_config:
        setup_logging("not-a-real-level")

    kwargs = basic_config.call_args.kwargs
    assert kwargs["level"] == logging.INFO
    assert kwargs["stream"] is sys.stderr
    assert "filename" not in kwargs


def test_setup_logging_uses_file_handler_when_log_file_is_set():
    """Supplying a log file should configure basicConfig for file output."""
    with patch("parazettel_mcp.utils.logging.basicConfig") as basic_config:
        setup_logging("debug", log_file="parazettel.log")

    kwargs = basic_config.call_args.kwargs
    assert kwargs["level"] == logging.DEBUG
    assert kwargs["filename"] == "parazettel.log"
    assert kwargs["filemode"] == "a"
    assert "stream" not in kwargs


def test_parse_tags_trims_values_and_skips_empty_entries():
    """parse_tags should normalize whitespace and ignore empty items."""
    assert parse_tags("") == []
    assert parse_tags(" alpha, ,beta , gamma ,, ") == ["alpha", "beta", "gamma"]


def test_format_note_for_display_includes_tags_and_link_descriptions():
    """format_note_for_display should render tags and both link formats."""
    link_with_description = SimpleNamespace(
        link_type=SimpleNamespace(value="reference"),
        target_id="note-2",
        description="Related note",
    )
    link_without_description = SimpleNamespace(
        link_type=SimpleNamespace(value="supports"),
        target_id="note-3",
        description="",
    )

    rendered = format_note_for_display(
        title="Test Note",
        id="note-1",
        content="Body text",
        tags=["alpha", "beta"],
        created_at=datetime(2026, 4, 22, 10, 0, 0),
        updated_at=datetime(2026, 4, 22, 11, 0, 0),
        links=[link_with_description, link_without_description],
    )

    assert "# Test Note" in rendered
    assert "Tags: alpha, beta" in rendered
    assert "Body text" in rendered
    assert "- reference: note-2 - Related note" in rendered
    assert "- supports: note-3" in rendered
