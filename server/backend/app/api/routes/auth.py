from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import generate_access_token, hash_access_token, hash_password, verify_password
from app.db.models import AccessToken, User

router = APIRouter()


class AuthRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token: str
    token_type: str = "bearer"
    user: UserResponse


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _create_user_and_token(db: Session, email: str, password: str) -> AuthResponse:
    email = _normalise_email(email)
    if not email or len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and a password of at least 6 characters are required.",
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        if existing.password_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        existing.password_hash = hash_password(password)
        db.commit()
        db.refresh(existing)
        user = existing
    else:
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)

    raw_token = generate_access_token()
    db.add(AccessToken(user_id=user.id, token_hash=hash_access_token(raw_token)))
    db.commit()

    return AuthResponse(
        access_token=raw_token,
        token=raw_token,
        user=UserResponse(id=str(user.id), email=user.email),
    )


def _authenticate(db: Session, email: str, password: str) -> AuthResponse:
    email = _normalise_email(email)
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    raw_token = generate_access_token()
    db.add(AccessToken(user_id=user.id, token_hash=hash_access_token(raw_token)))
    db.commit()

    return AuthResponse(
        access_token=raw_token,
        token=raw_token,
        user=UserResponse(id=str(user.id), email=user.email),
    )


@router.post("/api/auth/signup")
@router.post("/api/auth/register")
def signup(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return _create_user_and_token(db, request.email, request.password)


@router.post("/api/auth/login")
def login(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return _authenticate(db, request.email, request.password)


@router.post("/api/auth/token")
def token_grant(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> AuthResponse:
    return _authenticate(db, username, password)


@router.get("/api/auth/me")
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email)