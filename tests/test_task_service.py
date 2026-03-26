"""Tests for ZettelService action-item methods (Phase 2 / Phase 3)."""

import datetime

import pytest

from zettelkasten_mcp.models.schema import (
    LinkType,
    NoteSource,
    NoteStatus,
    NoteType,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def area(zettel_service):
    """A default area note used by most tests."""
    return zettel_service.create_area_note(
        title="Work", content="Work responsibilities."
    )


@pytest.fixture
def project(zettel_service, area):
    """A default project linked to the default area."""
    return zettel_service.create_project_note(
        title="Default Project", content="Project.", area_id=area.id
    )


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------


def test_create_task_basic(zettel_service, project):
    """create_task() creates a TASK-type note with correct fields."""
    task = zettel_service.create_task(
        title="Write unit tests",
        content="Cover all new service methods.",
        project_id=project.id,
        status=NoteStatus.READY,
        priority=2,
        estimated_minutes=45,
    )
    assert task.note_type == NoteType.TASK
    assert task.status == NoteStatus.READY
    assert task.priority == 2
    assert task.estimated_minutes == 45
    assert task.source == NoteSource.MANUAL
    assert task.project_id == project.id


def test_create_task_inbox_default(zettel_service, project):
    """create_task() defaults to INBOX status."""
    task = zettel_service.create_task(
        title="Quick capture", content="From my head.", project_id=project.id
    )
    assert task.status == NoteStatus.INBOX


def test_create_task_requires_project(zettel_service):
    """create_task() without project_id raises ValueError."""
    with pytest.raises(ValueError, match="project_id required"):
        zettel_service.create_task(title="Orphan task", content="No project.")


def test_create_task_autofills_area_from_project(zettel_service, project, area):
    """create_task() auto-fills area_id from the linked project."""
    task = zettel_service.create_task(
        title="Auto-area task", content=".", project_id=project.id
    )
    assert task.area_id == area.id


def test_create_task_links_to_project(zettel_service, project):
    """create_task(project_id=...) creates a bidirectional PART_OF/HAS_PART link."""
    task = zettel_service.create_task(
        title="Draft roadmap", content="Write the roadmap doc.", project_id=project.id
    )
    task_links = {lnk.link_type for lnk in zettel_service.get_note(task.id).links}
    project_links = {lnk.link_type for lnk in zettel_service.get_note(project.id).links}
    assert LinkType.PART_OF in task_links
    assert LinkType.HAS_PART in project_links


def test_create_task_with_remind_at(zettel_service, project):
    """remind_at field is stored and retrieved correctly."""
    remind = datetime.date(2026, 6, 1)
    task = zettel_service.create_task(
        title="Reminder task", content=".", project_id=project.id, remind_at=remind
    )
    retrieved = zettel_service.get_note(task.id)
    assert retrieved.remind_at == remind


# ---------------------------------------------------------------------------
# update_task_status
# ---------------------------------------------------------------------------


def test_update_task_status(zettel_service, project):
    """update_task_status() changes the status field."""
    task = zettel_service.create_task(
        title="Fix bug", content="Reproduce then fix.", project_id=project.id
    )
    updated = zettel_service.update_task_status(task.id, NoteStatus.ACTIVE)
    assert updated.status == NoteStatus.ACTIVE


def test_update_task_status_non_task_raises(zettel_service):
    """update_task_status() raises ValueError for non-task notes."""
    note = zettel_service.create_note("A permanent note", "Just a note.")
    with pytest.raises(ValueError, match="not a task"):
        zettel_service.update_task_status(note.id, NoteStatus.DONE)


def test_complete_non_recurring_task(zettel_service, project):
    """Completing a non-recurring task just marks it done — no new task spawned."""
    task = zettel_service.create_task(
        title="One-off task", content="Do once.", project_id=project.id
    )
    before_count = len(zettel_service.get_all_notes())
    zettel_service.update_task_status(task.id, NoteStatus.DONE)
    assert len(zettel_service.get_all_notes()) == before_count


def test_complete_recurring_task_spawns_new(zettel_service, project):
    """Completing a recurring task creates a new READY task with the next due date."""
    today = datetime.date.today()
    task = zettel_service.create_task(
        title="Weekly review",
        content="Review notes.",
        project_id=project.id,
        due_date=today,
        recurrence_rule="weekly",
    )
    before_count = len(zettel_service.get_all_notes())
    zettel_service.update_task_status(task.id, NoteStatus.DONE)
    assert len(zettel_service.get_all_notes()) == before_count + 1

    new_tasks = zettel_service.get_tasks(status=NoteStatus.READY)
    new_task = next(t for t in new_tasks if t.title == "Weekly review")
    assert new_task.recurrence_rule == "weekly"
    assert new_task.due_date == today + datetime.timedelta(weeks=1)
    assert new_task.source == NoteSource.RECURRING


# ---------------------------------------------------------------------------
# get_tasks
# ---------------------------------------------------------------------------


def test_get_tasks_filters_by_status(zettel_service, project):
    """get_tasks(status=...) returns only tasks with that status."""
    zettel_service.create_task(
        title="Inbox task", content=".", project_id=project.id, status=NoteStatus.INBOX
    )
    zettel_service.create_task(
        title="Active task",
        content=".",
        project_id=project.id,
        status=NoteStatus.ACTIVE,
    )
    zettel_service.create_task(
        title="Done task", content=".", project_id=project.id, status=NoteStatus.DONE
    )
    active = zettel_service.get_tasks(status=NoteStatus.ACTIVE)
    assert len(active) == 1
    assert active[0].title == "Active task"


def test_get_tasks_filters_by_project(zettel_service, area):
    """get_tasks(project_id=...) returns only tasks linked to that project."""
    p1 = zettel_service.create_project_note("Project A", ".", area_id=area.id)
    p2 = zettel_service.create_project_note("Project B", ".", area_id=area.id)
    task_in = zettel_service.create_task("In project A", ".", project_id=p1.id)
    zettel_service.create_task("In project B", ".", project_id=p2.id)

    tasks = zettel_service.get_tasks(project_id=p1.id)
    assert len(tasks) == 1
    assert tasks[0].id == task_in.id


# ---------------------------------------------------------------------------
# get_todays_tasks
# ---------------------------------------------------------------------------


def test_get_todays_tasks_returns_due_and_overdue(zettel_service, project):
    """get_todays_tasks() returns tasks due today and overdue, sorted by priority."""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)

    zettel_service.create_task(
        "Due today",
        ".",
        project_id=project.id,
        due_date=today,
        priority=1,
        status=NoteStatus.READY,
    )
    zettel_service.create_task(
        "Overdue",
        ".",
        project_id=project.id,
        due_date=yesterday,
        priority=3,
        status=NoteStatus.ACTIVE,
    )
    zettel_service.create_task(
        "Future", ".", project_id=project.id, due_date=tomorrow, status=NoteStatus.READY
    )

    tasks = zettel_service.get_todays_tasks(include_overdue=True)
    assert len(tasks) == 2
    assert tasks[0].title == "Overdue"  # priority 3 sorts before priority 1


def test_get_todays_tasks_includes_scheduled(zettel_service, project):
    """get_todays_tasks() includes SCHEDULED tasks due today."""
    today = datetime.date.today()
    zettel_service.create_task(
        "Scheduled today",
        ".",
        project_id=project.id,
        due_date=today,
        status=NoteStatus.SCHEDULED,
    )
    tasks = zettel_service.get_todays_tasks()
    assert any(t.title == "Scheduled today" for t in tasks)


def test_get_todays_tasks_excludes_done(zettel_service, project):
    """get_todays_tasks() excludes DONE and CANCELLED tasks."""
    today = datetime.date.today()
    zettel_service.create_task(
        "Done task", ".", project_id=project.id, due_date=today, status=NoteStatus.DONE
    )
    zettel_service.create_task(
        "Active task",
        ".",
        project_id=project.id,
        due_date=today,
        status=NoteStatus.ACTIVE,
    )
    tasks = zettel_service.get_todays_tasks()
    assert all(t.title != "Done task" for t in tasks)
    assert any(t.title == "Active task" for t in tasks)


# ---------------------------------------------------------------------------
# get_reminders
# ---------------------------------------------------------------------------


def test_get_reminders_returns_due_notes(zettel_service, project):
    """get_reminders() returns notes/tasks with remind_at <= today."""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)

    zettel_service.create_task(
        "Remind yesterday", ".", project_id=project.id, remind_at=yesterday
    )
    zettel_service.create_task(
        "Remind tomorrow", ".", project_id=project.id, remind_at=tomorrow
    )

    reminders = zettel_service.get_reminders()
    reminder_titles = {r.title for r in reminders}
    assert "Remind yesterday" in reminder_titles
    assert "Remind tomorrow" not in reminder_titles


# ---------------------------------------------------------------------------
# create_project_note + create_area_note
# ---------------------------------------------------------------------------


def test_create_project_note(zettel_service, area):
    """create_project_note() creates a PROJECT-type note with area link."""
    project = zettel_service.create_project_note(
        title="Launch feature",
        content="Ship by end of quarter.",
        outcome="Feature live in production.",
        deadline=datetime.date(2026, 6, 30),
        area_id=area.id,
    )
    assert project.note_type == NoteType.PROJECT
    assert project.metadata.get("outcome") == "Feature live in production."
    assert project.area_id == area.id
    project_links = {lnk.link_type for lnk in zettel_service.get_note(project.id).links}
    assert LinkType.PART_OF in project_links


def test_get_project_tasks(zettel_service, area):
    """get_project_tasks() returns tasks linked to the project."""
    p = zettel_service.create_project_note("Project Y", ".", area_id=area.id)
    t1 = zettel_service.create_task("Task 1", ".", project_id=p.id)
    t2 = zettel_service.create_task(
        "Task 2", ".", project_id=p.id, status=NoteStatus.DONE
    )

    all_tasks = zettel_service.get_project_tasks(p.id)
    assert {t.id for t in all_tasks} == {t1.id, t2.id}

    done_tasks = zettel_service.get_project_tasks(p.id, status=NoteStatus.DONE)
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
