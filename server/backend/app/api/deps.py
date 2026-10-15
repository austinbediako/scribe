from datetime import datetime, timedelta, timezone
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import hash_access_token
from app.db.models import AccessToken, User
from app.db.session import SessionLocal


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_bearer_scheme = HTTPBearer(auto_error=False)


def get_user_by_token(db: Session, token: str) -> User | None:
    token_hash = hash_access_token(token)
    access_token = db.query(AccessToken).filter(AccessToken.token_hash == token_hash).first()
    if access_token is None:
        return None
    token_age = datetime.now(timezone.utc) - access_token.created_at.replace(tzinfo=timezone.utc) if access_token.created_at.tzinfo is None else datetime.now(timezone.utc) - access_token.created_at
    if token_age > timedelta(days=30):
        db.delete(access_token)
        db.commit()
        return None
    return access_token.user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        return None
    return get_user_by_token(db, credentials.credentials)


def get_or_create_demo_user(db: Session) -> User:
    user = db.query(User).filter_by(email="demo@example.com").first()
    if user is None:
        user = User(email="demo@example.com", granola_user_id="granola-demo-user")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def resolve_request_user(db: Session, user: User | None) -> User:
    return user if user is not None else get_or_create_demo_user(db)