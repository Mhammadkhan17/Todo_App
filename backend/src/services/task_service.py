from datetime import date, datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.exceptions.custom_exceptions import (
    TaskNotFoundException,
    UserNotFoundException,
)
from src.models.task import Priority, Status, Task
from src.models.user import User


class TaskService:
    """User-scoped task operations shared by REST, chat, and MCP."""

    UPDATABLE_FIELDS = ("title", "description", "priority", "due_date", "status")

    @staticmethod
    def _require_user(session: Session, user_id: int) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise UserNotFoundException(user_id)
        return user

    @staticmethod
    def _get_task(session: Session, user_id: int, task_id: int) -> Task:
        task = (
            session.query(Task)
            .filter(Task.id == task_id, Task.user_id == user_id)
            .first()
        )
        if task is None:
            raise TaskNotFoundException(task_id)
        return task

    @staticmethod
    def create(
        session: Session,
        *,
        user_id: int,
        title: str,
        description: str | None = None,
        priority: Priority = Priority.MEDIUM,
        due_date: date | None = None,
    ) -> Task:
        TaskService._require_user(session, user_id)
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            status=Status.ACTIVE,
            user_id=user_id,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return task

    @staticmethod
    def list(
        session: Session,
        *,
        user_id: int,
        status: Status | None = None,
        priority: Priority | None = None,
        due_date_from: date | None = None,
        due_date_to: date | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Task], int]:
        TaskService._require_user(session, user_id)
        query = session.query(Task).filter(Task.user_id == user_id)

        if status is not None:
            query = query.filter(Task.status == status)
        if priority is not None:
            query = query.filter(Task.priority == priority)
        if due_date_from is not None:
            query = query.filter(Task.due_date >= due_date_from)
        if due_date_to is not None:
            query = query.filter(Task.due_date <= due_date_to)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )

        total = query.count()
        tasks = (
            query.order_by(Task.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return tasks, total

    @staticmethod
    def get(session: Session, *, user_id: int, task_id: int) -> Task:
        return TaskService._get_task(session, user_id, task_id)

    @staticmethod
    def update(
        session: Session,
        *,
        user_id: int,
        task_id: int,
        changes: dict,
    ) -> Task:
        task = TaskService._get_task(session, user_id, task_id)
        now = datetime.now(timezone.utc)

        for field in TaskService.UPDATABLE_FIELDS:
            if field not in changes:
                continue
            value = changes[field]
            setattr(task, field, value)

            if field == "status":
                if value == Status.COMPLETED:
                    task.completed_at = task.completed_at or now
                else:
                    task.completed_at = None

        task.updated_at = now
        session.commit()
        session.refresh(task)
        return task

    @staticmethod
    def set_completed(
        session: Session,
        *,
        user_id: int,
        task_id: int,
        completed: bool,
    ) -> Task:
        return TaskService.update(
            session,
            user_id=user_id,
            task_id=task_id,
            changes={"status": Status.COMPLETED if completed else Status.ACTIVE},
        )

    @staticmethod
    def toggle_completed(session: Session, *, user_id: int, task_id: int) -> Task:
        task = TaskService._get_task(session, user_id, task_id)
        return TaskService.set_completed(
            session,
            user_id=user_id,
            task_id=task_id,
            completed=task.status == Status.ACTIVE,
        )

    @staticmethod
    def soft_delete(session: Session, *, user_id: int, task_id: int) -> Task:
        return TaskService.update(
            session,
            user_id=user_id,
            task_id=task_id,
            changes={"status": Status.COMPLETED},
        )

    @staticmethod
    def delete(session: Session, *, user_id: int, task_id: int) -> None:
        task = TaskService._get_task(session, user_id, task_id)
        session.delete(task)
        session.commit()

    @staticmethod
    def summary(session: Session, *, user_id: int) -> dict:
        TaskService._require_user(session, user_id)
        base = session.query(func.count(Task.id)).filter(Task.user_id == user_id)

        total = base.scalar() or 0
        active = base.filter(Task.status == Status.ACTIVE).scalar() or 0
        completed = base.filter(Task.status == Status.COMPLETED).scalar() or 0
        high_priority = base.filter(Task.priority == Priority.HIGH).scalar() or 0
        overdue = (
            base.filter(
                Task.status == Status.ACTIVE,
                Task.due_date.is_not(None),
                Task.due_date < datetime.now(timezone.utc).date(),
            ).scalar()
            or 0
        )

        return {
            "total": total,
            "active": active,
            "completed": completed,
            "high_priority": high_priority,
            "overdue": overdue,
        }

    @staticmethod
    def to_dict(task: Task) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }
