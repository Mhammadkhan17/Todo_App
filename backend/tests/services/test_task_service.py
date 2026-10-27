from datetime import date

import pytest

from src.exceptions.custom_exceptions import TaskNotFoundException
from src.models.task import Priority, Status
from src.services.task_service import TaskService
from tests.helpers import create_user


def test_create_and_list_tasks(db_session):
    user = create_user(db_session)

    created = TaskService.create(
        db_session,
        user_id=user.id,
        title="Write report",
        priority=Priority.HIGH,
        due_date=date(2026, 11, 1),
    )

    tasks, total = TaskService.list(db_session, user_id=user.id)

    assert created.id is not None
    assert total == 1
    assert tasks[0].title == "Write report"
    assert tasks[0].priority == Priority.HIGH


def test_filters_and_search(db_session):
    user = create_user(db_session)
    TaskService.create(db_session, user_id=user.id, title="Buy milk", priority=Priority.LOW)
    TaskService.create(db_session, user_id=user.id, title="Pay rent", priority=Priority.HIGH)
    completed = TaskService.create(db_session, user_id=user.id, title="Call dentist")
    TaskService.set_completed(db_session, user_id=user.id, task_id=completed.id, completed=True)

    active, active_total = TaskService.list(
        db_session, user_id=user.id, status=Status.ACTIVE
    )
    high, high_total = TaskService.list(
        db_session, user_id=user.id, priority=Priority.HIGH
    )
    found, found_total = TaskService.list(
        db_session, user_id=user.id, search="milk"
    )

    assert active_total == 2
    assert all(task.status == Status.ACTIVE for task in active)
    assert high_total == 1
    assert high[0].title == "Pay rent"
    assert found_total == 1
    assert found[0].title == "Buy milk"


def test_update_changes_fields_and_timestamp(db_session):
    user = create_user(db_session)
    task = TaskService.create(db_session, user_id=user.id, title="Old title")
    before = task.updated_at

    updated = TaskService.update(
        db_session,
        user_id=user.id,
        task_id=task.id,
        changes={"title": "New title", "priority": Priority.LOW},
    )

    assert updated.title == "New title"
    assert updated.priority == Priority.LOW
    assert updated.updated_at != before


def test_complete_and_reopen(db_session):
    user = create_user(db_session)
    task = TaskService.create(db_session, user_id=user.id, title="Ship it")

    completed = TaskService.set_completed(
        db_session, user_id=user.id, task_id=task.id, completed=True
    )
    assert completed.status == Status.COMPLETED
    assert completed.completed_at is not None

    reopened = TaskService.set_completed(
        db_session, user_id=user.id, task_id=task.id, completed=False
    )
    assert reopened.status == Status.ACTIVE
    assert reopened.completed_at is None


def test_soft_delete_and_hard_delete(db_session):
    user = create_user(db_session)
    soft = TaskService.create(db_session, user_id=user.id, title="Soft")
    hard = TaskService.create(db_session, user_id=user.id, title="Hard")

    TaskService.soft_delete(db_session, user_id=user.id, task_id=soft.id)
    TaskService.delete(db_session, user_id=user.id, task_id=hard.id)

    assert TaskService.get(db_session, user_id=user.id, task_id=soft.id).status == Status.COMPLETED
    with pytest.raises(TaskNotFoundException):
        TaskService.get(db_session, user_id=user.id, task_id=hard.id)


def test_cross_user_access_is_denied(db_session):
    owner = create_user(db_session)
    other = create_user(db_session)
    task = TaskService.create(db_session, user_id=owner.id, title="Private")

    with pytest.raises(TaskNotFoundException):
        TaskService.get(db_session, user_id=other.id, task_id=task.id)


def test_summary_counts(db_session):
    user = create_user(db_session)
    TaskService.create(db_session, user_id=user.id, title="One", priority=Priority.HIGH)
    TaskService.create(db_session, user_id=user.id, title="Two")
    done = TaskService.create(db_session, user_id=user.id, title="Three")
    TaskService.set_completed(db_session, user_id=user.id, task_id=done.id, completed=True)

    summary = TaskService.summary(db_session, user_id=user.id)

    assert summary["total"] == 3
    assert summary["active"] == 2
    assert summary["completed"] == 1
    assert summary["high_priority"] == 1
