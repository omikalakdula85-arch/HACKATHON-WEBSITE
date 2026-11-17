import hashlib
import secrets
from datetime import timedelta
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

try:
    from .clock import utc_now
    from .database import get_db
    from .models import DemoSession, User
except ImportError:
    from clock import utc_now
    from database import get_db
    from models import DemoSession, User


SESSION_HOURS = 12


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_demo_session(db: Session, username: str) -> tuple[str, User]:
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo account not found.")
    token = secrets.token_urlsafe(32)
    db.query(DemoSession).filter(DemoSession.expires_at <= utc_now()).delete()
    db.add(DemoSession(
        token_digest=_digest(token),
        user_id=user.id,
        expires_at=utc_now() + timedelta(hours=SESSION_HOURS),
    ))
    db.commit()
    return token, user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer session token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session token is empty.")
    active_session = db.query(DemoSession).filter(
        DemoSession.token_digest == _digest(token),
        DemoSession.expires_at > utc_now(),
    ).first()
    if active_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, active_session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session account no longer exists.")
    return user


def require_roles(*roles: str) -> Callable[..., User]:
    def role_guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account role cannot access this operation.",
            )
        return user

    return role_guard
