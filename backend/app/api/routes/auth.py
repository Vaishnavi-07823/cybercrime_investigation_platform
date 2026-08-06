from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password, hash_password
from app.db.session import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserRead


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if db.scalar(select(User).where(User.email == payload.email.casefold())):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=payload.email.casefold(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="analyst",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.casefold()))
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    settings = get_settings()
    token = create_access_token(subject=user.id, role=user.role, email=user.email)
    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.access_token_minutes,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )
