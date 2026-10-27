from uuid import uuid4

from sqlmodel import Session

from src.models.user import User


def create_user(session: Session, full_name: str = "Test User") -> User:
    suffix = uuid4().hex[:10]
    user = User(
        email=f"{suffix}@example.com",
        username=f"user_{suffix}",
        password_hash="not-used-in-service-tests",
        full_name=full_name,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
