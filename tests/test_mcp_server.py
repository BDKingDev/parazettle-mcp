# tests/test_mcp_server.py
"""Tests for the MCP server implementation."""
from unittest.mock import MagicMock, call, patch

import pytest

from parazettel_mcp.models.schema import LinkType, NoteSource, NoteStatus, NoteType
from parazettel_mcp.server.mcp_server import ZettelkastenMcpServer


class TestMcpServer:
    """Tests for the ZettelkastenMcpServer class."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Capture the tool decorator functions when registering
        self.registered_tools = {}

        # Create a mock for FastMCP
        self.mock_mcp = MagicMock()

        # Mock the tool decorator to capture registered functions BEFORE server creation
        def mock_tool_decorator(*args, **kwargs):
            def tool_wrapper(func):
                # Store the function with its name
                name = kwargs.get("name")
                self.registered_tools[name] = func
                return func

            return tool_wrapper

        self.mock_mcp.tool = mock_tool_decorator

        # Mock the ZettelService and SearchService
        self.mock_zettel_service = MagicMock()
        self.mock_search_service = MagicMock()

        # Create patchers for FastMCP, ZettelService, and SearchService
        self.mcp_patcher = patch(
            "parazettel_mcp.server.mcp_server.FastMCP", return_value=self.mock_mcp
        )
        self.zettel_patcher = patch(
            "parazettel_mcp.server.mcp_server.ZettelService",
            return_value=self.mock_zettel_service,
        )
        self.search_patcher = patch(
            "parazettel_mcp.server.mcp_server.SearchService",
            return_value=self.mock_search_service,
        )

        # Start the patchers
        self.mcp_patcher.start()
        self.zettel_patcher.start()
        self.search_patcher.start()

        # Create a server instance AFTER setting up the mocks
        self.server = ZettelkastenMcpServer()

    def teardown_method(self):
        """Clean up after each test."""
        self.mcp_patcher.stop()
        self.zettel_patcher.stop()
        self.search_patcher.stop()

    def test_server_initialization(self):
        """Test server initialization."""
        # Check services are initialized
        assert self.mock_zettel_service.initialize.called
        assert self.mock_search_service.initialize.called

    def test_create_note_tool(self):
        """Test the pzk_create_note tool."""
        # Check the tool is registered
        assert "pzk_create_note" in self.registered_tools
        # Set up return value for create_note
        mock_note = MagicMock()
        mock_note.id = "test123"
        self.mock_zettel_service.create_note.return_value = mock_note
        # Call the tool function directly
        create_note_func = self.registered_tools["pzk_create_note"]
        result = create_note_func(
            title="Test Note",
            content="Test content",
            note_type="permanent",
            tags="tag1, tag2",
            source="transcript",
        )
        # Verify result
        assert "successfully" in result
        assert mock_note.id in result
        # Verify service call
        self.mock_zettel_service.create_note.assert_called_with(
            title="Test Note",
            content="Test content",
            note_type=NoteType.PERMANENT,
            tags=["tag1", "tag2"],
            source=NoteSource.TRANSCRIPT,
            status=None,
        )

    def test_create_note_tool_passes_status(self):
        """pzk_create_note forwards note status for knowledge-note triage."""
        mock_note = MagicMock()
        mock_note.id = "test123"
        self.mock_zettel_service.create_note.return_value = mock_note

        create_note_func = self.registered_tools["pzk_create_note"]
        result = create_note_func(
            title="Inbox Note",
            content="Captured for later processing.",
            note_type="permanent",
            source="transcript",
            status="inbox",
        )

        assert "successfully" in result
        self.mock_zettel_service.create_note.assert_called_with(
            title="Inbox Note",
            content="Captured for later processing.",
            note_type=NoteType.PERMANENT,
            tags=[],
            source=NoteSource.TRANSCRIPT,
            status=NoteStatus.INBOX,
        )

    def test_create_note_tool_rejects_invalid_status(self):
        """pzk_create_note returns the valid note-status list for bad values."""
        create_note_func = self.registered_tools["pzk_create_note"]

        result = create_note_func(
            title="Inbox Note",
            content="Captured for later processing.",
            note_type="permanent",
            source="transcript",
            status="flying",
        )

        assert "Invalid status" in result
        assert "inbox" in result
        self.mock_zettel_service.create_note.assert_not_called()

    def test_create_note_tool_requires_source_for_non_area(self):
        """pzk_create_note requires source for all note types except area."""
        create_note_func = self.registered_tools["pzk_create_note"]

        result = create_note_func(
            title="Test Note",
            content="Test content",
            note_type="permanent",
            tags="tag1, tag2",
        )

        assert "source is required" in result
        self.mock_zettel_service.create_note.assert_not_called()

    def test_create_note_tool_allows_area_without_source(self):
        """pzk_create_note allows area notes to omit source."""
        mock_note = MagicMock()
        mock_note.id = "area123"
        self.mock_zettel_service.create_note.return_value = mock_note

        create_note_func = self.registered_tools["pzk_create_note"]
        result = create_note_func(
            title="Household Systems",
            content="Ongoing responsibilities.",
            note_type="area",
            tags="home",
        )

        assert "successfully" in result
        self.mock_zettel_service.create_note.assert_called_with(
            title="Household Systems",
            content="Ongoing responsibilities.",
            note_type=NoteType.AREA,
            tags=["home"],
            source=NoteSource.MANUAL,
            status=None,
        )

    def test_create_note_tool_rejects_invalid_source(self):
        """pzk_create_note rejects unknown source values."""
        create_note_func = self.registered_tools["pzk_create_note"]

        result = create_note_func(
            title="Test Note",
            content="Test content",
            note_type="permanent",
            source="invalid",
        )

        assert "Invalid source" in result
        self.mock_zettel_service.create_note.assert_not_called()

    def test_create_project_tool_requires_and_passes_source(self):
        """pzk_create_project validates and forwards source."""
        assert "pzk_create_project" in self.registered_tools
        mock_project = MagicMock()
        mock_project.id = "project123"
        self.mock_zettel_service.create_project_note.return_value = mock_project

        create_project_func = self.registered_tools["pzk_create_project"]
        result = create_project_func(
            title="Launch feature",
            content="Ship by end of quarter.",
            source="transcript",
            tags="product, launch",
        )

        assert "successfully" in result
        self.mock_zettel_service.create_project_note.assert_called_with(
            title="Launch feature",
            content="Ship by end of quarter.",
            outcome=None,
            deadline=None,
            area_id=None,
            tags=["product", "launch"],
            source=NoteSource.TRANSCRIPT,
        )

    def test_create_project_tool_rejects_invalid_source(self):
        """pzk_create_project rejects unknown source values."""
        create_project_func = self.registered_tools["pzk_create_project"]

        result = create_project_func(
            title="Launch feature",
            content="Ship by end of quarter.",
            source="invalid",
        )

        assert "Invalid source" in result
        self.mock_zettel_service.create_project_note.assert_not_called()

    def test_update_note_tool_passes_status(self):
        """pzk_update_note forwards note status updates."""
        mock_note = MagicMock()
        mock_note.id = "note123"
        self.mock_zettel_service.get_note.return_value = mock_note
        self.mock_zettel_service.update_note.return_value = mock_note

        update_note_func = self.registered_tools["pzk_update_note"]
        result = update_note_func(note_id="note123", status="inbox")

        assert "updated successfully" in result
        self.mock_zettel_service.update_note.assert_called_with(
            note_id="note123",
            title=None,
            content=None,
            note_type=None,
            tags=None,
            status=NoteStatus.INBOX,
        )

    def test_update_note_tool_clears_status_with_empty_string(self):
        """pzk_update_note clears status when given an empty string."""
        mock_note = MagicMock()
        mock_note.id = "note123"
        self.mock_zettel_service.get_note.return_value = mock_note
        self.mock_zettel_service.update_note.return_value = mock_note

        update_note_func = self.registered_tools["pzk_update_note"]
        result = update_note_func(note_id="note123", status="")

        assert "updated successfully" in result
        self.mock_zettel_service.update_note.assert_called_with(
            note_id="note123",
            title=None,
            content=None,
            note_type=None,
            tags=None,
            status=None,
        )

    def test_update_note_tool_rejects_invalid_status(self):
        """pzk_update_note returns the valid note-status list for bad values."""
        mock_note = MagicMock()
        mock_note.id = "note123"
        self.mock_zettel_service.get_note.return_value = mock_note

        update_note_func = self.registered_tools["pzk_update_note"]
        result = update_note_func(note_id="note123", status="flying")

        assert "Invalid status" in result
        assert "inbox" in result
        self.mock_zettel_service.update_note.assert_not_called()

    def test_get_note_tool(self):
        """Test the pzk_get_note tool."""
        # Check the tool is registered
        assert "pzk_get_note" in self.registered_tools

        # Set up mock note
        mock_note = MagicMock()
        mock_note.id = "test123"
        mock_note.title = "Test Note"
        mock_note.content = "Test content"
        mock_note.note_type = NoteType.PERMANENT
        mock_note.created_at.isoformat.return_value = "2023-01-01T12:00:00"
        mock_note.updated_at.isoformat.return_value = "2023-01-01T12:30:00"
        mock_tag1 = MagicMock()
        mock_tag1.name = "tag1"
        mock_tag2 = MagicMock()
        mock_tag2.name = "tag2"
        mock_note.tags = [mock_tag1, mock_tag2]
        mock_note.links = []

        # Set up return value for get_note
        self.mock_zettel_service.get_note.return_value = mock_note

        # Call the tool function directly
        get_note_func = self.registered_tools["pzk_get_note"]
        result = get_note_func(identifier="test123")

        # Verify result — title appears in content body, not duplicated in header
        assert "ID: test123" in result
        assert "Test content" in result

        # Verify service call
        self.mock_zettel_service.get_note.assert_called_with("test123")

    def test_create_link_tool(self):
        """Test the pzk_create_link tool."""
        # Check the tool is registered
        assert "pzk_create_link" in self.registered_tools

        # Set up mock notes
        source_note = MagicMock()
        source_note.id = "source123"
        target_note = MagicMock()
        target_note.id = "target456"

        # Set up return value for create_link
        self.mock_zettel_service.create_link.return_value = (source_note, target_note)

        # Call the tool function directly
        create_link_func = self.registered_tools["pzk_create_link"]
        result = create_link_func(
            source_id="source123",
            target_id="target456",
            link_type="extends",
            description="Test link",
            bidirectional=True,
        )

        # Verify result
        assert "Bidirectional link created" in result
        assert "source123" in result
        assert "target456" in result

        # Verify service call
        self.mock_zettel_service.create_link.assert_called_with(
            source_id="source123",
            target_id="target456",
            link_type=LinkType.EXTENDS,
            description="Test link",
            bidirectional=True,
        )

    def test_search_notes_tool(self):
        """Test the pzk_search_notes tool."""
        # Check the tool is registered
        assert "pzk_search_notes" in self.registered_tools

        # Set up mock notes
        mock_note1 = MagicMock()
        mock_note1.id = "note1"
        mock_note1.title = "Note 1"
        mock_note1.content = "This is note 1 content"
        mock_tag1 = MagicMock()
        mock_tag1.name = "tag1"
        mock_tag2 = MagicMock()
        mock_tag2.name = "tag2"
        mock_note1.tags = [mock_tag1, mock_tag2]
        mock_note1.created_at.strftime.return_value = "2023-01-01"

        mock_note2 = MagicMock()
        mock_note2.id = "note2"
        mock_note2.title = "Note 2"
        mock_note2.content = "This is note 2 content"
        # mock_note2.tags = [MagicMock(name="tag1")]
        mock_tag1 = MagicMock()
        mock_tag1.name = "tag1"
        mock_note2.tags = [mock_tag1]
        mock_note2.created_at.strftime.return_value = "2023-01-02"

        # Set up mock search results
        mock_result1 = MagicMock()
        mock_result1.note = mock_note1
        mock_result2 = MagicMock()
        mock_result2.note = mock_note2

        self.mock_search_service.search_combined.return_value = [
            mock_result1,
            mock_result2,
        ]

        # Call the tool function directly
        search_notes_func = self.registered_tools["pzk_search_notes"]
        result = search_notes_func(
            query="test query",
            tags="tag1, tag2",
            note_type="permanent",
            status="ready",
            project_id="project123",
            area_id="area456",
            limit=10,
        )

        # Verify result
        assert "Found 2 matching notes" in result
        assert "Note 1" in result
        assert "Note 2" in result

        # Verify service call
        self.mock_search_service.search_combined.assert_called_with(
            text="test query",
            tags=["tag1", "tag2"],
            note_type=NoteType.PERMANENT,
            status=NoteStatus.READY,
            project_id="project123",
            area_id="area456",
        )

    def test_search_notes_rejects_invalid_status(self):
        """pzk_search_notes returns the valid status list for invalid status values."""
        search_notes_func = self.registered_tools["pzk_search_notes"]
        result = search_notes_func(status="flying")

        assert "Invalid status" in result
        assert "inbox" in result
        self.mock_search_service.search_combined.assert_not_called()

    def test_create_task_tool_response_includes_title_and_id(self):
        """pzk_create_task returns a human-readable success message with title and ID."""
        mock_task = MagicMock()
        mock_task.id = "task123"
        mock_task.title = "Weekly review"
        self.mock_zettel_service.create_task.return_value = mock_task

        create_task_func = self.registered_tools["pzk_create_task"]
        result = create_task_func(
            title="Weekly review",
            content="Review projects and notes.",
            project_id="project123",
        )

        assert "Weekly review" in result
        assert "task123" in result
        self.mock_zettel_service.create_task.assert_called_with(
            title="Weekly review",
            content="Review projects and notes.",
            status=NoteStatus.INBOX,
            tags=[],
            project_id="project123",
            area_id=None,
            due_date=None,
            remind_at=None,
            priority=None,
            recurrence_rule=None,
            estimated_minutes=None,
            source=NoteSource.MANUAL,
        )

    def test_update_task_tool_registered(self):
        """pzk_update_task tool should be registered."""
        assert "pzk_update_task" in self.registered_tools

    def test_update_task_updates_due_date(self):
        """pzk_update_task updates due_date on a task note."""
        mock_task = MagicMock()
        mock_task.id = "task001"
        mock_task.note_type = NoteType.TASK
        mock_task.tags = []
        self.mock_zettel_service.get_note.return_value = mock_task
        self.mock_zettel_service.repository = MagicMock()

        fn = self.registered_tools["pzk_update_task"]
        result = fn(task_id="task001", due_date="2026-04-01")

        assert "updated successfully" in result
        assert mock_task.due_date is not None
        self.mock_zettel_service.repository.update.assert_called_once_with(mock_task)

    def test_update_task_rejects_non_task_note(self):
        """pzk_update_task returns an error if the note is not a task."""
        mock_note = MagicMock()
        mock_note.note_type = NoteType.PERMANENT
        self.mock_zettel_service.get_note.return_value = mock_note

        fn = self.registered_tools["pzk_update_task"]
        result = fn(task_id="note001", priority=3)

        assert "not a task" in result
        self.mock_zettel_service.repository.update.assert_not_called()

    def test_update_task_rejects_invalid_due_date(self):
        """pzk_update_task returns an error for a malformed due_date."""
        mock_task = MagicMock()
        mock_task.note_type = NoteType.TASK
        self.mock_zettel_service.get_note.return_value = mock_task

        fn = self.registered_tools["pzk_update_task"]
        result = fn(task_id="task001", due_date="not-a-date")

        assert "Invalid due_date" in result
        self.mock_zettel_service.repository.update.assert_not_called()

    def test_update_task_rejects_invalid_status(self):
        """pzk_update_task returns an error for an unrecognised status value."""
        mock_task = MagicMock()
        mock_task.note_type = NoteType.TASK
        self.mock_zettel_service.get_note.return_value = mock_task

        fn = self.registered_tools["pzk_update_task"]
        result = fn(task_id="task001", status="flying")

        assert "Invalid status" in result
        self.mock_zettel_service.repository.update.assert_not_called()

    def test_update_task_routes_status_through_service(self):
        """pzk_update_task calls update_task_status (not repository.update) for status changes."""
        mock_task = MagicMock()
        mock_task.note_type = NoteType.TASK
        mock_task.recurrence_rule = None
        self.mock_zettel_service.get_note.return_value = mock_task
        self.mock_zettel_service.update_task_status.return_value = mock_task

        fn = self.registered_tools["pzk_update_task"]
        result = fn(task_id="task001", status="done")

        assert "done" in result
        self.mock_zettel_service.update_task_status.assert_called_once()
        # repository.update should NOT be called for a status-only change
        self.mock_zettel_service.repository.update.assert_not_called()

    def test_update_task_announces_recurring_spawn(self):
        """pzk_update_task includes 'recurring instance created' when a recurring task is completed."""
        mock_task = MagicMock()
        mock_task.note_type = NoteType.TASK
        mock_task.recurrence_rule = "weekly"
        self.mock_zettel_service.get_note.return_value = mock_task
        self.mock_zettel_service.update_task_status.return_value = mock_task

        fn = self.registered_tools["pzk_update_task"]
        result = fn(task_id="task001", status="done")

        assert "recurring instance created" in result

    def test_update_task_status_tool_removed(self):
        """pzk_update_task_status should no longer be registered; use pzk_update_task instead."""
        assert "pzk_update_task_status" not in self.registered_tools

    def test_error_handling(self):
        """Test error handling in the server."""
        # Test ValueError handling
        value_error = ValueError("Invalid input")
        result = self.server.format_error_response(value_error)
        assert "Error: Invalid input" in result

        # Test IOError handling
        io_error = IOError("File not found")
        result = self.server.format_error_response(io_error)
        assert "Error: File not found" in result

        # Test general exception handling
        general_error = Exception("Something went wrong")
        result = self.server.format_error_response(general_error)
        assert "Error: Something went wrong" in result
