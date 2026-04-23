"""Tests for the CLI entrypoint."""

import argparse
import shutil
import sys
from pathlib import Path
from uuid import uuid4
from unittest.mock import MagicMock

import pytest

import parazettel_mcp.main as main_module
from parazettel_mcp.config import config


@pytest.fixture
def workspace_temp_dir():
    """Create a writable temp directory inside the repo workspace."""
    base_dir = Path(".tmp") / "test-main" / str(uuid4())
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield base_dir
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def restore_config():
    """Restore global config mutations made by main/update_config tests."""
    original_notes_dir = config.notes_dir
    original_database_path = config.database_path
    yield
    config.notes_dir = original_notes_dir
    config.database_path = original_database_path


def test_parse_args_reads_env_defaults(monkeypatch):
    """parse_args should use Parazettel env vars as defaults."""
    monkeypatch.setenv("PARAZETTEL_NOTES_DIR", "env-notes")
    monkeypatch.setenv("PARAZETTEL_DATABASE_PATH", "env-db.sqlite")
    monkeypatch.setenv("PARAZETTEL_LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(sys, "argv", ["parazettel"])

    args = main_module.parse_args()

    assert args.notes_dir == "env-notes"
    assert args.database_path == "env-db.sqlite"
    assert args.log_level == "DEBUG"


def test_update_config_updates_paths():
    """update_config should rewrite the global notes/db paths."""
    args = argparse.Namespace(
        notes_dir="custom-notes",
        database_path="custom-db.sqlite",
        log_level="INFO",
    )

    main_module.update_config(args)

    assert str(config.notes_dir) == "custom-notes"
    assert str(config.database_path) == "custom-db.sqlite"


def test_main_initializes_and_runs_server(monkeypatch, workspace_temp_dir):
    """main should set up logging, initialize the DB, run the server, and clean up."""
    notes_dir = workspace_temp_dir / "notes"
    database_path = workspace_temp_dir / "db" / "test.sqlite"
    args = argparse.Namespace(
        notes_dir=str(notes_dir),
        database_path=str(database_path),
        log_level="DEBUG",
    )
    engine = MagicMock()
    server = MagicMock()
    setup_logging = MagicMock()
    init_db = MagicMock(return_value=engine)
    server_factory = MagicMock(return_value=server)

    monkeypatch.setattr(main_module, "parse_args", lambda: args)
    monkeypatch.setattr(main_module, "setup_logging", setup_logging)
    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "ZettelkastenMcpServer", server_factory)

    main_module.main()

    assert notes_dir.exists()
    assert database_path.parent.exists()
    setup_logging.assert_called_once_with("DEBUG")
    init_db.assert_called_once_with()
    engine.dispose.assert_called_once_with()
    server_factory.assert_called_once_with()
    server.run.assert_called_once_with()
    server.close.assert_called_once_with()


def test_main_exits_when_db_init_fails(monkeypatch, workspace_temp_dir):
    """main should exit with code 1 when DB initialization fails."""
    args = argparse.Namespace(
        notes_dir=str(workspace_temp_dir / "notes"),
        database_path=str(workspace_temp_dir / "db" / "test.sqlite"),
        log_level="INFO",
    )
    setup_logging = MagicMock()
    init_db = MagicMock(side_effect=RuntimeError("db init failed"))
    server_factory = MagicMock()

    monkeypatch.setattr(main_module, "parse_args", lambda: args)
    monkeypatch.setattr(main_module, "setup_logging", setup_logging)
    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "ZettelkastenMcpServer", server_factory)

    with pytest.raises(SystemExit) as excinfo:
        main_module.main()

    assert excinfo.value.code == 1
    setup_logging.assert_called_once_with("INFO")
    init_db.assert_called_once_with()
    server_factory.assert_not_called()


def test_main_closes_server_when_run_fails(monkeypatch, workspace_temp_dir):
    """main should dispose the engine and close the server on runtime failures."""
    args = argparse.Namespace(
        notes_dir=str(workspace_temp_dir / "notes"),
        database_path=str(workspace_temp_dir / "db" / "test.sqlite"),
        log_level="WARNING",
    )
    engine = MagicMock()
    server = MagicMock()
    server.run.side_effect = RuntimeError("run failed")
    setup_logging = MagicMock()
    init_db = MagicMock(return_value=engine)
    server_factory = MagicMock(return_value=server)

    monkeypatch.setattr(main_module, "parse_args", lambda: args)
    monkeypatch.setattr(main_module, "setup_logging", setup_logging)
    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "ZettelkastenMcpServer", server_factory)

    with pytest.raises(SystemExit) as excinfo:
        main_module.main()

    assert excinfo.value.code == 1
    engine.dispose.assert_called_once_with()
    server.run.assert_called_once_with()
    server.close.assert_called_once_with()
