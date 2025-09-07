from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.schemas.auth import RegisterIn, LoginIn, MeOut
from backend.auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
)
from backend.models import Usuario
from backend.database import get_db

router = APIRouter()


@router.post("/register", status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email_lower = payload.email.lower()
    if db.query(Usuario).filter(Usuario.email_lower == email_lower).first():
        raise HTTPException(
            status_code=400, detail="Ya existe una cuenta con ese email."
        )
    user = Usuario(
        username=payload.username.strip(),
        email=payload.email,
        email_lower=email_lower,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    return {"ok": True}


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = (
        db.query(Usuario).filter(Usuario.email_lower == payload.email.lower()).first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")
    token = create_access_token({"sub": user.email_lower})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=MeOut)
def me(current_user: Usuario = Depends(get_current_user)):
    return MeOut(username=current_user.username or "", email=current_user.email)
