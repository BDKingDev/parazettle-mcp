#!/usr/bin/env python
"""Main entry point for the Zettelkasten MCP server."""
import argparse
import logging
import os
import sys
from pathlib import Path

from parazettel_mcp.config import config
from parazettel_mcp.models.db_models import init_db
from parazettel_mcp.server.mcp_server import ZettelkastenMcpServer
from parazettel_mcp.utils import setup_logging


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Zettelkasten MCP Server")
    parser.add_argument(
        "--notes-dir",
        help="Directory for storing note files",
        type=str,
        default=os.environ.get("PARAZETTEL_NOTES_DIR"),
    )
    parser.add_argument(
        "--database-path",
        help="SQLite database file path",
        type=str,
        default=os.environ.get("PARAZETTEL_DATABASE_PATH"),
    )
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("PARAZETTEL_LOG_LEVEL", "INFO"),
    )
    return parser.parse_args()


def update_config(args):
    """Update the global config with command line arguments."""
    if args.notes_dir:
        config.notes_dir = Path(args.notes_dir)
    if args.database_path:
        config.database_path = Path(args.database_path)


def main():
    """Run the Zettelkasten MCP server."""
    # Parse arguments and update config
    args = parse_args()
    update_config(args)

    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Ensure directories exist
    notes_dir = config.get_absolute_path(config.notes_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)
    db_dir = config.get_absolute_path(config.database_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # Initialize database schema
    try:
        logger.info(f"Using SQLite database: {config.get_db_url()}")
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Create and run the MCP server
    try:
        logger.info("Starting Zettelkasten MCP server")
        server = ZettelkastenMcpServer()
        server.run()
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
