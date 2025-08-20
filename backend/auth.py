from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.future import select
from sqlalchemy import func
from backend.models import Usuario
from backend.database import get_db
from sqlalchemy.orm import Session
import os

# ────────────────────────────────────────────
# 🔐 Clave secreta: obligatoria en .env / Render
# ────────────────────────────────────────────
import secrets

SECRET_KEY = os.getenv("SECRET_KEY") or (secrets.token_urlsafe(32) if os.getenv("ENV") != "production" else None)

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no definido: crea la variable en tu archivo .env "
        "y en Render > Environment antes de iniciar la API."
    )

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def hashear_password(password: str):
    return pwd_context.hash(password)


def verificar_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)


def crear_token(data: dict):
    """Genera un JWT con los datos proporcionados."""
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def obtener_usuario_por_email(email: str, db: Session):
    email = (email or "").strip().lower()
    return db.query(Usuario).filter(func.lower(Usuario.email) == email).first()

def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obtiene el usuario actual a partir de un token JWT.

    Si la variable de entorno ``ALLOW_ANON_USER`` está establecida, permite el
    acceso sin token retornando un usuario básico temporal. Esto se usa
    principalmente para ejecutar pruebas automatizadas sin depender de un flujo
    de autenticación completo.
    """

    credentials_exc = HTTPException(
        status_code=401,
        detail="Token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        if os.getenv("ALLOW_ANON_USER") == "1":
            return Usuario(email="anon@example.com", hashed_password="", plan="basico")
        raise credentials_exc

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exc
        email = email.strip().lower()
        user = obtener_usuario_por_email(email, db)
        if user is None:
            raise credentials_exc
        return user
    except JWTError:
        raise credentials_exc
