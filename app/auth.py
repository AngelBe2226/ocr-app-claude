from fastapi import Depends, Request
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Settings, User


class NotAuthenticated(Exception):
    pass


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise NotAuthenticated()
    return user


def login_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not bcrypt.verify(password, user.password_hash):
        return None
    return user


def get_or_create_settings(db: Session, user: User) -> Settings:
    settings = db.get(Settings, user.id)
    if not settings:
        settings = Settings(user_id=user.id, theme="light", accent_key="teal")
        db.add(settings)
        db.commit()
    return settings
