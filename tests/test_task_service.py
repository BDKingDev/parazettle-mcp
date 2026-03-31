"""Tests for ZettelService action-item methods (Phase 2 / Phase 3)."""

import datetime

import pytest

from parazettel_mcp.models.schema import (
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
    returned_task_links = {lnk.link_type for lnk in task.links}
    task_links = {lnk.link_type for lnk in zettel_service.get_note(task.id).links}
    project_links = {lnk.link_type for lnk in zettel_service.get_note(project.id).links}
    assert LinkType.PART_OF in returned_task_links
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
    assert new_task.project_id == project.id
    assert new_task.area_id == project.area_id
    assert LinkType.PART_OF in {
        link.link_type for link in zettel_service.get_note(new_task.id).links
    }


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
        source=NoteSource.TRANSCRIPT,
    )
    assert project.note_type == NoteType.PROJECT
    assert project.metadata.get("outcome") == "Feature live in production."
    assert project.area_id == area.id
    assert project.source == NoteSource.TRANSCRIPT
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


# ---------------------------------------------------------------------------
# pzk_update_task (repository-level task field updates)
# ---------------------------------------------------------------------------


def test_update_task_due_date(zettel_service, project):
    """Updating due_date via repository.update persists through get()."""
    task = zettel_service.create_task("Update due date", ".", project_id=project.id)
    task.due_date = datetime.date(2026, 4, 1)
    zettel_service.repository.update(task)

    refreshed = zettel_service.get_note(task.id)
    assert refreshed.due_date == datetime.date(2026, 4, 1)


def test_update_task_priority_and_estimated_minutes(zettel_service, project):
    """Updating priority and estimated_minutes persists through get()."""
    task = zettel_service.create_task("Update priority", ".", project_id=project.id)
    task.priority = 4
    task.estimated_minutes = 420
    zettel_service.repository.update(task)

    refreshed = zettel_service.get_note(task.id)
    assert refreshed.priority == 4
    assert refreshed.estimated_minutes == 420


def test_update_task_multiple_fields_at_once(zettel_service, project):
    """Multiple task fields can be updated in a single repository.update call."""
    task = zettel_service.create_task("Multi-field update", ".", project_id=project.id)
    task.due_date = datetime.date(2026, 4, 2)
    task.priority = 3
    task.status = NoteStatus.READY
    task.estimated_minutes = 180
    zettel_service.repository.update(task)

    refreshed = zettel_service.get_note(task.id)
    assert refreshed.due_date == datetime.date(2026, 4, 2)
    assert refreshed.priority == 3
    assert refreshed.status == NoteStatus.READY
    assert refreshed.estimated_minutes == 180


def test_update_task_status_done_still_spawns_recurring(zettel_service, project):
    """Completing a recurring task via repository.update + update_task_status spawns next instance."""
    today = datetime.date.today()
    task = zettel_service.create_task(
        "Recurring via update",
        ".",
        project_id=project.id,
        due_date=today,
        recurrence_rule="weekly",
    )
    # Simulate pzk_update_task: update non-status fields, then call update_task_status
    task.priority = 2
    zettel_service.repository.update(task)
    zettel_service.update_task_status(task.id, NoteStatus.DONE)

    new_tasks = zettel_service.get_tasks(status=NoteStatus.READY)
    assert any(t.title == "Recurring via update" for t in new_tasks)
    spawned = next(t for t in new_tasks if t.title == "Recurring via update")
    assert spawned.due_date == today + datetime.timedelta(weeks=1)
    assert spawned.priority == 2  # priority carried over from the completed instance
    assert spawned.project_id == project.id
    assert spawned.area_id == project.area_id
    assert spawned.id in {task.id for task in zettel_service.get_project_tasks(project.id)}


def test_update_task_appears_in_todays_tasks_after_due_date_set(zettel_service, project):
    """A task with no due date does not appear in get_todays_tasks(); setting due_date=today makes it appear."""
    import datetime

    task = zettel_service.create_task(
        "No due date yet", ".", project_id=project.id, status=NoteStatus.READY
    )
    assert task.id not in {t.id for t in zettel_service.get_todays_tasks()}

    task.due_date = datetime.date.today()
    zettel_service.repository.update(task)

    assert task.id in {t.id for t in zettel_service.get_todays_tasks()}


def test_create_area_note(zettel_service):
    """create_area_note() creates an AREA-type note."""
    area = zettel_service.create_area_note(
        title="Health",
        content="Maintain physical and mental health.",
        cadence="weekly review",
    )
    assert area.note_type == NoteType.AREA
    assert area.metadata.get("cadence") == "weekly review"
