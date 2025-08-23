from time import sleep
from backend.database import Base, engine, SessionLocal
from backend.db import guardar_memoria_usuario_pg, obtener_memoria_usuario_pg
from backend.models import UsuarioMemoria


def test_usuario_memoria_crud():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    email = "test@demo.com"
    desc1 = "primera"
    guardar_memoria_usuario_pg(email, desc1)
    assert obtener_memoria_usuario_pg(email) == desc1

    with SessionLocal() as db:
        first = db.query(UsuarioMemoria).filter_by(email_lower=email).first().updated_at

    sleep(1)
    desc2 = "segunda"
    guardar_memoria_usuario_pg(email, desc2)
    assert obtener_memoria_usuario_pg(email) == desc2

    with SessionLocal() as db:
        second = db.query(UsuarioMemoria).filter_by(email_lower=email).first().updated_at

    assert second > first
