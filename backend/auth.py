from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.future import select
from backend.models import Usuario
from backend.database import get_db
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hashear_password(password: str):
    return pwd_context.hash(password)


def verificar_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)


def crear_token(data: dict):
    """Genera un JWT con los datos proporcionados."""
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


async def obtener_usuario_por_email(email: str, db):
    query = select(Usuario).where(Usuario.email == email)
    result = await db.execute(query)
    return result.scalars().first()


async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    """Devuelve el usuario autenticado o lanza HTTP 401."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        user = await obtener_usuario_por_email(email, db)
        if user is None:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
