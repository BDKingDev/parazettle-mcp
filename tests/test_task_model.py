"""Tests for action-item schema additions (Phase 2)."""

import datetime

import pytest

from parazettel_mcp.models.schema import (
    LinkType,
    Note,
    NoteSource,
    NoteStatus,
    NoteType,
    Tag,
)

# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------


def test_task_status_values():
    """NoteStatus enum has all expected values."""
    assert NoteStatus.INBOX.value == "inbox"
    assert NoteStatus.READY.value == "ready"
    assert NoteStatus.ACTIVE.value == "active"
    assert NoteStatus.WAITING.value == "waiting"
    assert NoteStatus.SCHEDULED.value == "scheduled"
    assert NoteStatus.SOMEDAY.value == "someday"
    assert NoteStatus.DONE.value == "done"
    assert NoteStatus.CANCELLED.value == "cancelled"
    assert NoteStatus.ARCHIVED.value == "archived"
    assert NoteStatus.EVERGREEN.value == "evergreen"


def test_note_source_values():
    """NoteSource enum has the expected values."""
    assert NoteSource.MANUAL.value == "manual"
    assert NoteSource.INBOX.value == "inbox"
    assert NoteSource.RECURRING.value == "recurring"


def test_action_note_types():
    """NoteType includes TASK, PROJECT, AREA."""
    assert NoteType.TASK.value == "task"
    assert NoteType.PROJECT.value == "project"
    assert NoteType.AREA.value == "area"


def test_action_link_types():
    """LinkType includes PART_OF, HAS_PART, BLOCKS, BLOCKED_BY."""
    assert LinkType.PART_OF.value == "part_of"
    assert LinkType.HAS_PART.value == "has_part"
    assert LinkType.BLOCKS.value == "blocks"
    assert LinkType.BLOCKED_BY.value == "blocked_by"


# ---------------------------------------------------------------------------
# Note model with action-item fields
# ---------------------------------------------------------------------------


def test_task_note_creation():
    """A task Note can be created with action-item fields."""
    note = Note(
        title="Write tests",
        content="Cover all new service methods.",
        note_type=NoteType.TASK,
        status=NoteStatus.READY,
        source=NoteSource.MANUAL,
        due_date=datetime.date(2026, 4, 1),
        priority=2,
        recurrence_rule="weekly",
        estimated_minutes=30,
    )
    assert note.note_type == NoteType.TASK
    assert note.status == NoteStatus.READY
    assert note.source == NoteSource.MANUAL
    assert note.due_date == datetime.date(2026, 4, 1)
    assert note.priority == 2
    assert note.recurrence_rule == "weekly"
    assert note.estimated_minutes == 30


def test_knowledge_note_defaults():
    """A regular knowledge note has None/MANUAL defaults for action-item fields."""
    note = Note(title="Zettelkasten", content="A method for note-taking.")
    assert note.status is None
    assert note.source == NoteSource.MANUAL
    assert note.due_date is None
    assert note.priority is None
    assert note.recurrence_rule is None
    assert note.estimated_minutes is None


# ---------------------------------------------------------------------------
# Frontmatter round-trip through repository
# ---------------------------------------------------------------------------


def test_task_fields_round_trip_through_frontmatter(note_repository):
    """Action-item fields survive _note_to_markdown / _parse_note_from_markdown."""
    note = Note(
        title="Frontmatter Round-trip",
        content="Task body.",
        note_type=NoteType.TASK,
        status=NoteStatus.ACTIVE,
        source=NoteSource.EMAIL,
        due_date=datetime.date(2026, 5, 10),
        priority=3,
        recurrence_rule="monthly",
        estimated_minutes=60,
    )
    saved = note_repository.create(note)
    retrieved = note_repository.get(saved.id)
    assert retrieved is not None
    assert retrieved.note_type == NoteType.TASK
    assert retrieved.status == NoteStatus.ACTIVE
    assert retrieved.source == NoteSource.EMAIL
    assert retrieved.due_date == datetime.date(2026, 5, 10)
    assert retrieved.priority == 3
    assert retrieved.recurrence_rule == "monthly"
    assert retrieved.estimated_minutes == 60


def test_knowledge_note_unchanged_after_schema_change(note_repository):
    """Existing knowledge notes still parse correctly with no action-item fields."""
    note = Note(
        title="Regular Knowledge Note",
        content="This is a permanent note.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="knowledge")],
    )
    saved = note_repository.create(note)
    retrieved = note_repository.get(saved.id)
    assert retrieved is not None
    assert retrieved.note_type == NoteType.PERMANENT
    assert retrieved.status is None
    assert retrieved.source == NoteSource.MANUAL
    assert retrieved.due_date is None


def test_inbox_status_is_first_triage_state():
    """INBOX is a distinct state from READY — it means 'captured, not yet triaged'."""
    inbox_note = Note(title="Capture", content="Raw idea.", status=NoteStatus.INBOX)
    ready_note = Note(
        title="Triaged", content="Decided to do.", status=NoteStatus.READY
    )
    assert inbox_note.status != ready_note.status
    assert inbox_note.status == NoteStatus.INBOX
    assert ready_note.status == NoteStatus.READY


def test_note_source_extended_values():
    """NoteSource includes new source types from Phase 3."""
    assert NoteSource.TRANSCRIPT.value == "transcript"
    assert NoteSource.BOOK.value == "book"
    assert NoteSource.ARTICLE.value == "article"
    assert NoteSource.CHAT.value == "chat"
    assert NoteSource.WEB.value == "web"
    assert NoteSource.PDF.value == "pdf"


def test_remind_at_round_trips_through_frontmatter(note_repository):
    """remind_at field survives _note_to_markdown / _parse_note_from_markdown."""
    remind = datetime.date(2026, 8, 15)
    note = Note(title="Remind Me", content="Check this later.", remind_at=remind)
    saved = note_repository.create(note)
    retrieved = note_repository.get(saved.id)
    assert retrieved is not None
    assert retrieved.remind_at == remind


def test_project_id_and_area_id_round_trip(note_repository):
    """project_id and area_id survive frontmatter and DB round-trip."""
    note = Note(
        title="PARA Routing Test",
        content=".",
        project_id="proj-123",
        area_id="area-456",
    )
    saved = note_repository.create(note)
    retrieved = note_repository.get(saved.id)
    assert retrieved.project_id == "proj-123"
    assert retrieved.area_id == "area-456"

    # Also verify DB-backed path (search)
    results = note_repository.search(title="PARA Routing Test")
    assert len(results) == 1
    assert results[0].project_id == "proj-123"
    assert results[0].area_id == "area-456"


def test_new_link_types_have_inverses(zettel_service):
    """PART_OF/HAS_PART and BLOCKS/BLOCKED_BY create correct bidirectional links."""
    task = zettel_service.create_note("Task A", "Do something.", NoteType.TASK)
    project = zettel_service.create_note("Project X", "Outcome.", NoteType.PROJECT)
    zettel_service.create_link(
        task.id, project.id, LinkType.PART_OF, bidirectional=True
    )

    task_links = {lnk.link_type for lnk in zettel_service.get_note(task.id).links}
    project_links = {lnk.link_type for lnk in zettel_service.get_note(project.id).links}
    assert LinkType.PART_OF in task_links
    assert LinkType.HAS_PART in project_links
