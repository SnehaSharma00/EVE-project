from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return db.scalar(select(User).where(User.id == user_id))

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email.lower().strip()))

    @staticmethod
    def create(db: Session, user_in: UserCreate, password_hash: str) -> User:
        user = User(
            email=user_in.email.lower().strip(),
            password_hash=password_hash,
            full_name=user_in.full_name.strip(),
            role=user_in.role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
