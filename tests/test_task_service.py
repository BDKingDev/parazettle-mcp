"""Tests for ZettelService action-item methods (Phase 2)."""

import datetime

import pytest

from zettelkasten_mcp.models.schema import (
    LinkType,
    NoteSource,
    NoteType,
    TaskStatus,
)


def test_create_task_basic(zettel_service):
    """create_task() creates a TASK-type note with correct fields."""
    task = zettel_service.create_task(
        title="Write unit tests",
        content="Cover all new service methods.",
        status=TaskStatus.READY,
        priority=2,
        estimated_minutes=45,
    )
    assert task.note_type == NoteType.TASK
    assert task.status == TaskStatus.READY
    assert task.priority == 2
    assert task.estimated_minutes == 45
    assert task.source == NoteSource.MANUAL


def test_create_task_inbox_default(zettel_service):
    """create_task() defaults to INBOX status."""
    task = zettel_service.create_task(title="Quick capture", content="From my head.")
    assert task.status == TaskStatus.INBOX


def test_create_task_links_to_project(zettel_service):
    """create_task(project_id=...) creates a bidirectional PART_OF/HAS_PART link."""
    project = zettel_service.create_project_note(
        title="Q2 Planning", content="Plan the quarter."
    )
    task = zettel_service.create_task(
        title="Draft roadmap", content="Write the roadmap doc.", project_id=project.id
    )
    task_links = {lnk.link_type for lnk in zettel_service.get_note(task.id).links}
    project_links = {lnk.link_type for lnk in zettel_service.get_note(project.id).links}
    assert LinkType.PART_OF in task_links
    assert LinkType.HAS_PART in project_links


def test_update_task_status(zettel_service):
    """update_task_status() changes the status field."""
    task = zettel_service.create_task(title="Fix bug", content="Reproduce then fix.")
    updated = zettel_service.update_task_status(task.id, TaskStatus.ACTIVE)
    assert updated.status == TaskStatus.ACTIVE


def test_update_task_status_non_task_raises(zettel_service):
    """update_task_status() raises ValueError for non-task notes."""
    note = zettel_service.create_note("A permanent note", "Just a note.")
    with pytest.raises(ValueError, match="not a task"):
        zettel_service.update_task_status(note.id, TaskStatus.DONE)


def test_complete_non_recurring_task(zettel_service):
    """Completing a non-recurring task just marks it done — no new task spawned."""
    task = zettel_service.create_task(title="One-off task", content="Do once.")
    before_count = len(zettel_service.get_all_notes())
    zettel_service.update_task_status(task.id, TaskStatus.DONE)
    after_count = len(zettel_service.get_all_notes())
    assert after_count == before_count


def test_complete_recurring_task_spawns_new(zettel_service):
    """Completing a recurring task creates a new READY task with the next due date."""
    today = datetime.date.today()
    task = zettel_service.create_task(
        title="Weekly review",
        content="Review notes.",
        due_date=today,
        recurrence_rule="weekly",
    )
    before_count = len(zettel_service.get_all_notes())
    zettel_service.update_task_status(task.id, TaskStatus.DONE)
    after_count = len(zettel_service.get_all_notes())
    assert after_count == before_count + 1

    new_tasks = zettel_service.get_tasks(status=TaskStatus.READY)
    assert len(new_tasks) == 1
    new_task = new_tasks[0]
    assert new_task.title == "Weekly review"
    assert new_task.recurrence_rule == "weekly"
    assert new_task.due_date == today + datetime.timedelta(weeks=1)
    assert new_task.source == NoteSource.RECURRING


def test_get_tasks_filters_by_status(zettel_service):
    """get_tasks(status=...) returns only tasks with that status."""
    zettel_service.create_task(title="Inbox task", content=".", status=TaskStatus.INBOX)
    zettel_service.create_task(
        title="Active task", content=".", status=TaskStatus.ACTIVE
    )
    zettel_service.create_task(title="Done task", content=".", status=TaskStatus.DONE)

    active = zettel_service.get_tasks(status=TaskStatus.ACTIVE)
    assert len(active) == 1
    assert active[0].title == "Active task"


def test_get_tasks_filters_by_project(zettel_service):
    """get_tasks(project_id=...) returns only tasks linked to that project."""
    project = zettel_service.create_project_note("My Project", "Goals.")
    task_in = zettel_service.create_task(
        title="In project", content=".", project_id=project.id
    )
    zettel_service.create_task(title="Not in project", content=".")

    tasks = zettel_service.get_tasks(project_id=project.id)
    assert len(tasks) == 1
    assert tasks[0].id == task_in.id


def test_get_todays_tasks_returns_due_and_overdue(zettel_service):
    """get_todays_tasks() returns tasks due today and overdue, sorted by priority."""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)

    zettel_service.create_task(
        "Due today", ".", due_date=today, priority=1, status=TaskStatus.READY
    )
    zettel_service.create_task(
        "Overdue", ".", due_date=yesterday, priority=3, status=TaskStatus.ACTIVE
    )
    zettel_service.create_task(
        "Future", ".", due_date=tomorrow, status=TaskStatus.READY
    )

    tasks = zettel_service.get_todays_tasks(include_overdue=True)
    assert len(tasks) == 2
    # Priority 3 (overdue) should sort before priority 1 (today)
    assert tasks[0].title == "Overdue"


def test_get_todays_tasks_excludes_done(zettel_service):
    """get_todays_tasks() excludes DONE and CANCELLED tasks."""
    today = datetime.date.today()
    zettel_service.create_task("Done task", ".", due_date=today, status=TaskStatus.DONE)
    zettel_service.create_task(
        "Active task", ".", due_date=today, status=TaskStatus.ACTIVE
    )

    tasks = zettel_service.get_todays_tasks()
    assert all(t.title != "Done task" for t in tasks)
    assert any(t.title == "Active task" for t in tasks)


def test_create_project_note(zettel_service):
    """create_project_note() creates a PROJECT-type note."""
    project = zettel_service.create_project_note(
        title="Launch feature",
        content="Ship by end of quarter.",
        outcome="Feature live in production.",
        deadline=datetime.date(2026, 6, 30),
    )
    assert project.note_type == NoteType.PROJECT
    assert project.metadata.get("outcome") == "Feature live in production."


def test_get_project_tasks(zettel_service):
    """get_project_tasks() returns tasks linked to the project."""
    project = zettel_service.create_project_note("Project Y", ".")
    t1 = zettel_service.create_task("Task 1", ".", project_id=project.id)
    t2 = zettel_service.create_task(
        "Task 2", ".", project_id=project.id, status=TaskStatus.DONE
    )
    zettel_service.create_task("Unlinked task", ".")

    all_tasks = zettel_service.get_project_tasks(project.id)
    assert {t.id for t in all_tasks} == {t1.id, t2.id}

    done_tasks = zettel_service.get_project_tasks(project.id, status=TaskStatus.DONE)
    assert len(done_tasks) == 1
    assert done_tasks[0].id == t2.id


def test_create_area_note(zettel_service):
    """create_area_note() creates an AREA-type note."""
    area = zettel_service.create_area_note(
        title="Health",
        content="Maintain physical and mental health.",
        cadence="weekly review",
    )
    assert area.note_type == NoteType.AREA
    assert area.metadata.get("cadence") == "weekly review"
