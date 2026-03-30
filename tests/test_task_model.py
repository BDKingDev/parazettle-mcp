"""Tests for action-item schema additions (Phase 2)."""

import datetime

import pytest

from zettelkasten_mcp.models.schema import (
    LinkType,
    Note,
    NoteSource,
    NoteType,
    Tag,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------


def test_task_status_values():
    """TaskStatus enum has the expected values."""
    assert TaskStatus.INBOX.value == "inbox"
    assert TaskStatus.READY.value == "ready"
    assert TaskStatus.ACTIVE.value == "active"
    assert TaskStatus.WAITING.value == "waiting"
    assert TaskStatus.SOMEDAY.value == "someday"
    assert TaskStatus.DONE.value == "done"
    assert TaskStatus.CANCELLED.value == "cancelled"


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
        status=TaskStatus.READY,
        source=NoteSource.MANUAL,
        due_date=datetime.date(2026, 4, 1),
        priority=2,
        recurrence_rule="weekly",
        estimated_minutes=30,
    )
    assert note.note_type == NoteType.TASK
    assert note.status == TaskStatus.READY
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
        status=TaskStatus.ACTIVE,
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
    assert retrieved.status == TaskStatus.ACTIVE
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
    inbox_note = Note(title="Capture", content="Raw idea.", status=TaskStatus.INBOX)
    ready_note = Note(
        title="Triaged", content="Decided to do.", status=TaskStatus.READY
    )
    assert inbox_note.status != ready_note.status
    assert inbox_note.status == TaskStatus.INBOX
    assert ready_note.status == TaskStatus.READY


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
