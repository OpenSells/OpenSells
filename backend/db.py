import os
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, OperationalError

try:  # pragma: no cover - dependency availability
    from psycopg2.errors import UndefinedColumn
except Exception:  # pragma: no cover
    class UndefinedColumn(Exception):
        pass

from backend.database import SessionLocal
from backend.models import LeadTarea, UsuarioMemoria, LeadExtraido
from backend.startup_migrations import (
    ensure_estado_contacto_column,
    ensure_lead_tarea_auto_column,
)

load_dotenv()

DB_PATH = "backend/historial.db"

# Advertir si existe memoria de usuario en el archivo SQLite obsoleto
if os.path.exists(DB_PATH):
    try:
        with sqlite3.connect(DB_PATH) as _db:
            cur = _db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='usuario_memoria'"
            )
            if cur.fetchone():
                count = _db.execute("SELECT COUNT(*) FROM usuario_memoria").fetchone()[0]
                if count > 0:
                    logging.warning(
                        "Se detectó 'usuario_memoria' en %s con %d registros. "
                        "Ejecuta scripts/migrar_memoria_sqlite_a_postgres.py; esta tabla ya no se usa.",
                        DB_PATH,
                        count,
                    )
    except sqlite3.Error:
        pass

logger = logging.getLogger(__name__)

def crear_tablas_si_no_existen():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            filename TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS lead_tarea (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            dominio TEXT,
            texto TEXT NOT NULL,
            fecha TEXT,
            completado INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            tipo TEXT DEFAULT 'lead',
            nicho TEXT,
            prioridad TEXT DEFAULT 'media'
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS lead_historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            dominio TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS lead_info_extra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dominio TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            informacion TEXT,
            user_email TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        db.commit()

from datetime import datetime

def guardar_tarea_lead_postgres(
    email: str,
    texto: str,
    fecha: str = None,
    dominio: str = None,
    tipo: str = "lead",
    nicho: str = None,
    prioridad: str = "media",
    auto: bool = False,
    db=None,
):
    timestamp = datetime.utcnow().isoformat()
    nueva_tarea = LeadTarea(
        email=email,
        user_email_lower=(email or "").strip().lower(),
        dominio=dominio,
        texto=texto,
        fecha=fecha,
        completado=False,
        timestamp=timestamp,
        tipo=tipo,
        nicho=nicho,
        prioridad=prioridad,
        auto=auto,
    )
    db.add(nueva_tarea)
    db.commit()

def obtener_todas_tareas_pendientes_postgres(
    email: str,
    db: Session,
    tipo: str = "todas",
    solo_pendientes: bool = True,
):
    def _query():
        q = (
            db.query(LeadTarea, LeadExtraido)
            .outerjoin(
                LeadExtraido,
                and_(
                    LeadTarea.dominio == LeadExtraido.url,
                    LeadTarea.user_email_lower == LeadExtraido.user_email_lower,
                ),
            )
            .filter(LeadTarea.user_email_lower == email)
        )

        if solo_pendientes:
            q = q.filter(LeadTarea.completado == False)  # noqa: E712

        if tipo == "general":
            q = q.filter(LeadTarea.tipo == "general")
        elif tipo == "nicho":
            q = q.filter(LeadTarea.tipo == "nicho")
        elif tipo == "lead":
            q = q.filter(LeadTarea.tipo == "lead")

        return q.order_by(
            LeadTarea.completado.asc(),
            LeadTarea.prioridad.asc(),
            LeadTarea.fecha.is_(None),
            LeadTarea.fecha.asc(),
            LeadTarea.timestamp.desc(),
        ).all()

    try:
        filas = _query()
    except (ProgrammingError, OperationalError) as e:
        if isinstance(getattr(e, "orig", None), UndefinedColumn) or "no such column" in str(getattr(e, "orig", "")):
            logger.warning("columna auto ausente; intentando autocompletar migración")
            ensure_lead_tarea_auto_column(db.get_bind())
            filas = _query()
        else:
            raise

    resultado = []
    for t, lead in filas:
        resultado.append(
            {
                "id": t.id,
                "dominio": t.dominio,
                "texto": t.texto,
                "fecha": t.fecha,
                "completado": t.completado,
                "timestamp": t.timestamp,
                "tipo": t.tipo,
                "nicho": t.nicho,
                "prioridad": t.prioridad,
                "lead_url": lead.url if lead else None,
                "auto": bool(getattr(t, "auto", False)),
            }
        )

    prio_map = {"alta": 0, "media": 1, "baja": 2}
    resultado.sort(
        key=lambda t: (
            t.get("completado"),
            prio_map.get(t.get("prioridad"), 999),
            not t.get("auto", False),
            t.get("fecha") is None,
            t.get("fecha"),
            t.get("timestamp"),
        )
    )
    return resultado

def obtener_tareas_lead_postgres(email: str, dominio: str, db: Session):
    def _query():
        return (
            db.query(LeadTarea)
            .filter(LeadTarea.user_email_lower == email, LeadTarea.dominio == dominio)
            .order_by(LeadTarea.timestamp.desc())
            .all()
        )

    try:
        resultados = _query()
    except (ProgrammingError, OperationalError) as e:
        if isinstance(getattr(e, "orig", None), UndefinedColumn) or "no such column" in str(getattr(e, "orig", "")):
            logger.warning("columna auto ausente; intentando autocompletar migración")
            ensure_lead_tarea_auto_column(db.get_bind())
            resultados = _query()
        else:
            raise

    return [
        {
            "id": tarea.id,
            "texto": tarea.texto,
            "fecha": tarea.fecha,
            "completado": tarea.completado,
            "timestamp": tarea.timestamp,
            "tipo": tarea.tipo or "lead",
            "prioridad": tarea.prioridad or "media",
            "dominio": tarea.dominio,
            "auto": bool(getattr(tarea, "auto", False)),
        }
        for tarea in resultados
    ]

def marcar_tarea_completada_postgres(email: str, tarea_id: int, db: Session):
    def _query():
        return db.query(LeadTarea).filter(
            LeadTarea.id == tarea_id,
            LeadTarea.user_email_lower == email
        ).first()

    try:
        tarea = _query()
    except (ProgrammingError, OperationalError) as e:
        if isinstance(getattr(e, "orig", None), UndefinedColumn) or "no such column" in str(getattr(e, "orig", "")):
            logger.warning("columna auto ausente; intentando autocompletar migración")
            ensure_lead_tarea_auto_column(db.get_bind())
            tarea = _query()
        else:
            raise

    if tarea:
        tarea.completado = True
        db.commit()

def guardar_exportacion(user_email: str, filename: str):
    with sqlite3.connect(DB_PATH) as db:
        timestamp = datetime.utcnow().isoformat()
        db.execute(
            "INSERT INTO historial (user_email, filename, timestamp) VALUES (?, ?, ?)",
            (user_email, filename, timestamp)
        )
        db.commit()

def guardar_leads_extraidos(
    user_email: str, dominios: list[str], nicho: str, nicho_original: str, db: Session
):
    """Guardar una lista de dominios como leads extraídos.

    Lanza una excepción si ocurre algún error o si no se inserta ningún registro
    nuevo aun cuando se proporcionaron dominios.
    """

    user_email_lower = (user_email or "").strip().lower()
    nuevos = []
    auto_task_enabled = os.getenv("AUTO_CONTACT_TASK_ENABLED", "true").lower() == "true"
    for dominio in dominios:
        existe = (
            db.query(LeadExtraido)
            .filter_by(user_email_lower=user_email_lower, url=dominio, nicho=nicho)
            .first()
        )
        if not existe:
            nuevo = LeadExtraido(
                user_email=user_email,
                user_email_lower=user_email_lower,
                url=dominio,
                nicho=nicho,
                nicho_original=nicho_original,
                estado_contacto="pendiente",
            )
            db.add(nuevo)
            nuevos.append(nuevo)

            if auto_task_enabled:
                titulo = f"Contactar lead: {dominio}"
                def _query_tarea():
                    return (
                        db.query(LeadTarea)
                        .filter(
                            LeadTarea.user_email_lower == user_email_lower,
                            LeadTarea.dominio == dominio,
                            LeadTarea.texto == titulo,
                            LeadTarea.auto.is_(True),
                            LeadTarea.completado.is_(False),
                        )
                        .first()
                    )

                try:
                    existe_tarea = _query_tarea()
                except (ProgrammingError, OperationalError) as e:
                    if isinstance(getattr(e, "orig", None), UndefinedColumn) or "no such column" in str(getattr(e, "orig", "")):
                        logger.warning("columna auto ausente; intentando autocompletar migración")
                        ensure_lead_tarea_auto_column(db.get_bind())
                        existe_tarea = _query_tarea()
                    else:
                        raise
                if not existe_tarea:
                    tarea = LeadTarea(
                        email=user_email,
                        user_email_lower=user_email_lower,
                        dominio=dominio,
                        texto=titulo,
                        completado=False,
                        tipo="lead",
                        nicho=nicho,
                        prioridad="media",
                        auto=True,
                    )
                    db.add(tarea)

    if dominios and not nuevos:
        raise ValueError("No se guardaron leads nuevos")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

def obtener_historial(user_email: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT filename, timestamp FROM historial
            WHERE user_email = ?
            ORDER BY timestamp DESC
        """, (user_email,))
        rows = cursor.fetchall()
        return [{"filename": row[0], "timestamp": row[1]} for row in rows]

def obtener_nichos_usuario(user_email: str, db: Session):
    def _query():
        return (
            db.query(
                LeadExtraido.nicho,
                func.max(LeadExtraido.nicho_original).label("nicho_original"),
            )
            .filter(LeadExtraido.user_email_lower == user_email)
            .group_by(LeadExtraido.nicho)
            .order_by(func.max(LeadExtraido.timestamp).desc())
            .all()
        )

    try:
        subquery = _query()
    except (ProgrammingError, OperationalError) as e:
        if isinstance(getattr(e, "orig", None), UndefinedColumn) or "no such column" in str(
            getattr(e, "orig", "")
        ):
            logger.warning(
                "columna estado_contacto ausente; intentando autocompletar migración"
            )
            ensure_estado_contacto_column(db.get_bind())
            subquery = _query()
        else:
            raise

    return [{"nicho": row.nicho, "nicho_original": row.nicho_original} for row in subquery]

def obtener_leads_por_nicho(
    user_email: str, nicho: str, db: Session, estado_contacto: str | None = None
):
    def _query():
        query = (
            db.query(LeadExtraido)
            .filter(LeadExtraido.user_email_lower == user_email, LeadExtraido.nicho == nicho)
        )
        if estado_contacto:
            query = query.filter(LeadExtraido.estado_contacto == estado_contacto)
        return query.order_by(LeadExtraido.timestamp.desc()).all()

    try:
        resultados = _query()
    except (ProgrammingError, OperationalError) as e:
        if isinstance(getattr(e, "orig", None), UndefinedColumn) or "no such column" in str(
            getattr(e, "orig", "")
        ):
            logger.warning(
                "columna estado_contacto ausente; intentando autocompletar migración"
            )
            ensure_estado_contacto_column(db.get_bind())
            resultados = _query()
        else:
            raise

    return [
        {
            "url": lead.url,
            "timestamp": str(lead.timestamp) if lead.timestamp else "",
            "estado_contacto": lead.estado_contacto,
        }
        for lead in resultados
    ]

def eliminar_nicho(user_email: str, nicho: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND nicho = ?
        """, (user_email, nicho))
        db.commit()

from backend.models import LeadExtraido

def eliminar_nicho_postgres(user_email: str, nicho: str, db: Session):
    """Eliminar todas las filas asociadas a un nicho para un usuario."""
    (
        db.query(LeadExtraido)
        .filter(LeadExtraido.user_email_lower == user_email, LeadExtraido.nicho == nicho)
        .delete(synchronize_session=False)
    )
    db.commit()

def obtener_urls_extraidas_por_nicho(user_email: str, nicho: str, db: Session):
    resultados = (
        db.query(LeadExtraido.url)
        .filter(LeadExtraido.user_email_lower == user_email, LeadExtraido.nicho == nicho)
        .all()
    )
    return [row[0] for row in resultados]

def guardar_estado_lead(email: str, url: str, estado: str):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            INSERT INTO lead_estado (email, url, estado, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email, url) DO UPDATE SET
                estado = excluded.estado,
                timestamp = excluded.timestamp
        """, (email, url, estado, timestamp))
        db.commit()

def obtener_estado_lead(email: str, url: str) -> str:
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT estado FROM lead_estado
            WHERE email = ? AND url = ?
        """, (email, url))
        row = cursor.fetchone()
        return row[0] if row else None

def obtener_nichos_para_url(user_email: str, url: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT DISTINCT nicho_original FROM leads_extraidos
            WHERE user_email = ? AND url = ?
        """, (user_email, url))
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def guardar_nota_lead(email: str, url: str, nota: str):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            INSERT INTO lead_nota (email, url, nota, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email, url) DO UPDATE SET
                nota = excluded.nota,
                timestamp = excluded.timestamp
        """, (email, url, nota, timestamp))
        db.commit()

from backend.models import LeadNota

def guardar_nota_lead_postgres(email: str, url: str, nota: str, db: Session):
    email_lower = (email or "").strip().lower()
    existente = db.query(LeadNota).filter_by(user_email_lower=email_lower, url=url).first()
    if existente:
        existente.nota = nota
    else:
        nueva = LeadNota(email=email, url=url, nota=nota)
        db.add(nueva)
    db.commit()

def obtener_nota_lead(email: str, url: str) -> str:
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT nota FROM lead_nota
            WHERE email = ? AND url = ?
        """, (email, url))
        row = cursor.fetchone()
        return row[0] if row else ""

def obtener_nota_lead_postgres(email: str, url: str, db: Session) -> str:
    email_lower = (email or "").strip().lower()
    nota = db.query(LeadNota).filter_by(user_email_lower=email_lower, url=url).first()
    return nota.nota if nota else ""

def buscar_leads_global(email: str, query: str):
    query = f"%{query.lower()}%"
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT DISTINCT le.url
            FROM leads_extraidos le
            LEFT JOIN lead_estado es ON le.url = es.url AND le.user_email = es.email
            LEFT JOIN lead_nota nt ON le.url = nt.url AND le.user_email = nt.email
            WHERE le.user_email = ?
            AND (
                LOWER(le.url) LIKE ?
                OR LOWER(nt.nota) LIKE ?
                OR LOWER(es.estado) LIKE ?
            )
            ORDER BY le.timestamp DESC
        """, (email, query, query, query))
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def buscar_leads_global_postgres(email: str, query: str, db: Session) -> list[str]:
    query = f"%{query.lower()}%"
    resultados = (
        db.query(LeadExtraido.url)
        .outerjoin(
            LeadNota,
            (LeadNota.url == LeadExtraido.url) & (LeadNota.user_email_lower == LeadExtraido.user_email_lower)
        )
        .filter(
            LeadExtraido.user_email_lower == email,
            (
                LeadExtraido.url.ilike(query) |
                LeadNota.nota.ilike(query)
            )
        )
        .distinct()
        .all()
    )
    return [r[0] for r in resultados]

def obtener_tareas_pendientes(email: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT id, dominio, texto, fecha, timestamp, tipo, nicho, prioridad
            FROM lead_tarea
            WHERE email = ? AND completado = 0
            ORDER BY 
                CASE prioridad
                    WHEN 'alta' THEN 0
                    WHEN 'media' THEN 1
                    WHEN 'baja' THEN 2
                    ELSE 3
                END,
                fecha IS NULL, fecha ASC, timestamp DESC
        """, (email,))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "dominio": row[1],
                "texto": row[2],
                "fecha": row[3],
                "timestamp": row[4],
                "tipo": row[5],
                "nicho": row[6],
                "prioridad": row[7]
            } for row in rows
        ]

def obtener_todas_tareas_pendientes(email: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT id, dominio, texto, fecha, completado, timestamp, tipo, nicho, prioridad
            FROM lead_tarea
            WHERE email = ?
            ORDER BY completado, 
                     CASE prioridad
                         WHEN 'alta' THEN 0
                         WHEN 'media' THEN 1
                         WHEN 'baja' THEN 2
                         ELSE 3
                     END,
                     fecha IS NULL, fecha ASC, timestamp DESC
        """, (email,))
        rows = cursor.fetchall()
        col_names = [column[0] for column in cursor.description]
        tareas = [dict(zip(col_names, row)) for row in rows]

        # Añadir nota a cada tarea si existe
        for tarea in tareas:
            dominio = tarea.get("dominio")
            if dominio:  # solo buscar nota si hay dominio
                nota_cursor = db.execute("""
                    SELECT nota FROM lead_nota WHERE email = ? AND url = ?
                """, (email, dominio))
                nota_row = nota_cursor.fetchone()
                if nota_row:
                    tarea["nota"] = nota_row[0]

        return tareas

def guardar_evento_historial(email: str, dominio: str, tipo: str, descripcion: str):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            INSERT INTO lead_historial (email, dominio, tipo, descripcion, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (email, dominio, tipo, descripcion, timestamp))
        db.commit()

from backend.models import LeadHistorial

from datetime import datetime

def guardar_evento_historial_postgres(email: str, dominio: str, tipo: str, descripcion: str, db: Session):
    evento = LeadHistorial(
        email=email,
        dominio=dominio,
        tipo=tipo,
        descripcion=descripcion,
        timestamp=datetime.utcnow().isoformat()
    )
    db.add(evento)
    db.commit()

def obtener_historial_por_dominio(email: str, dominio: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT tipo, descripcion, timestamp
            FROM lead_historial
            WHERE email = ? AND dominio = ?
            ORDER BY timestamp DESC
        """, (email, dominio))
        rows = cursor.fetchall()
        return [
            {"tipo": row[0], "descripcion": row[1], "timestamp": row[2]}
            for row in rows
        ]

def obtener_historial_por_dominio_postgres(email: str, dominio: str, db: Session):
    eventos = (
        db.query(LeadHistorial)
        .filter(LeadHistorial.user_email_lower == email, LeadHistorial.dominio == dominio)
        .order_by(LeadHistorial.timestamp.desc())
        .all()
    )

    return [
        {
            "tipo": evento.tipo,
            "descripcion": evento.descripcion,
            "timestamp": evento.timestamp
        }
        for evento in eventos
    ]

def obtener_tarea_por_id_postgres(email: str, tarea_id: int, db: Session):
    tarea = (
        db.query(LeadTarea)
        .filter(LeadTarea.id == tarea_id, LeadTarea.user_email_lower == email)
        .first()
    )
    if tarea:
        return {
            "id": tarea.id,
            "dominio": tarea.dominio,
            "texto": tarea.texto,
            "tipo": tarea.tipo,
            "nicho": tarea.nicho,
            "auto": bool(getattr(tarea, "auto", False)),
        }
    return None


def guardar_memoria_usuario_pg(email_lower: str, descripcion: str) -> None:
    """Guarda o actualiza la memoria del usuario en PostgreSQL."""
    email_lower = (email_lower or "").strip().lower()
    with SessionLocal() as db:
        UsuarioMemoria.__table__.create(bind=db.bind, checkfirst=True)
        insert_fn = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        stmt = (
            insert_fn(UsuarioMemoria)
            .values(email_lower=email_lower, descripcion=descripcion, updated_at=func.now())
            .on_conflict_do_update(
                index_elements=[UsuarioMemoria.email_lower],
                set_={"descripcion": descripcion, "updated_at": func.now()},
            )
        )
        db.execute(stmt)
        db.commit()


def obtener_memoria_usuario_pg(email_lower: str) -> str | None:
    """Obtiene la memoria del usuario desde PostgreSQL."""
    email_lower = (email_lower or "").strip().lower()
    with SessionLocal() as db:
        UsuarioMemoria.__table__.create(bind=db.bind, checkfirst=True)
        memoria = (
            db.query(UsuarioMemoria.descripcion)
            .filter(UsuarioMemoria.email_lower == email_lower)
            .scalar()
        )
        return memoria

def obtener_historial_por_tipo(email: str, tipo: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT tipo, descripcion, timestamp
            FROM lead_historial
            WHERE email = ? AND tipo = ?
            ORDER BY timestamp DESC
        """, (email, tipo))
        rows = cursor.fetchall()
        return [{"tipo": row[0], "descripcion": row[1], "timestamp": row[2]} for row in rows]

def obtener_historial_por_tipo_postgres(email: str, tipo: str, db: Session):
    eventos = (
        db.query(LeadHistorial)
        .filter(LeadHistorial.user_email_lower == email, LeadHistorial.tipo == tipo)
        .order_by(LeadHistorial.timestamp.desc())
        .all()
    )
    return [{"tipo": e.tipo, "descripcion": e.descripcion, "timestamp": e.timestamp} for e in eventos]

def obtener_historial_por_nicho_postgres(email: str, nicho: str, db: Session):
    eventos = (
        db.query(LeadHistorial)
        .filter(LeadHistorial.user_email_lower == email, LeadHistorial.tipo == "nicho", LeadHistorial.dominio == nicho)
        .order_by(LeadHistorial.timestamp.desc())
        .all()
    )
    return [{"tipo": e.tipo, "descripcion": e.descripcion, "timestamp": e.timestamp} for e in eventos]

from backend.models import LeadExtraido

def eliminar_lead_de_nicho(user_email: str, dominio: str, nicho: str, db: Session):
    email_lower = (user_email or "").strip().lower()
    db.query(LeadExtraido).filter_by(
        user_email_lower=email_lower,
        url=dominio,
        nicho=nicho
    ).delete()
    db.commit()

from urllib.parse import urlparse

def extraer_dominio_base(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        dominio = urlparse(url).netloc
        return dominio.replace("www.", "").strip()
    else:
        return url.replace("www.", "").strip()

def mover_lead_en_bd(user_email: str, dominio_original: str, nicho_origen: str, nicho_destino: str, nicho_original_destino: str, db: Session):
    from backend.models import LeadExtraido, LeadTarea

    dominio_limpio = extraer_dominio_base(dominio_original)

    # 🗑️ Eliminar del nicho original
    email_lower = (user_email or "").strip().lower()
    db.query(LeadExtraido).filter_by(user_email_lower=email_lower, url=dominio_limpio, nicho=nicho_origen).delete()

    # ✅ Insertar en el nuevo nicho
    nuevo = LeadExtraido(
        user_email=user_email,
        user_email_lower=email_lower,
        url=dominio_limpio,
        timestamp=datetime.utcnow().isoformat(),
        nicho=nicho_destino,
        nicho_original=nicho_original_destino
    )
    db.add(nuevo)

    # 🔁 Actualizar tareas relacionadas
    db.query(LeadTarea).filter_by(user_email_lower=email_lower, dominio=dominio_limpio).update({"nicho": nicho_destino})

    db.commit()

from urllib.parse import urlparse

def normalizar_dominio(url: str) -> str:
    if not url:
        return ""
    url = url.lower().strip()
    if url.startswith("http://") or url.startswith("https://"):
        dominio = urlparse(url).netloc
    else:
        dominio = urlparse("http://" + url).netloc
    dominio = dominio.replace("www.", "").strip()
    return dominio.split("/")[0]  # Elimina todo lo que haya después de /

def editar_nombre_nicho(email: str, nicho_actual: str, nuevo_nombre: str):
    from .main import normalizar_nicho
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            UPDATE leads_extraidos
            SET nicho_original = ?, nicho = ?
            WHERE user_email = ? AND nicho = ?
        """, (nuevo_nombre, normalizar_nicho(nuevo_nombre), email, normalizar_nicho(nicho_actual)))
        db.commit()

def eliminar_lead_completamente(email: str, dominio: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND url = ?
        """, (email, dominio))

        db.execute("""
            DELETE FROM lead_nota
            WHERE email = ? AND url = ?
        """, (email, dominio))

        db.execute("""
            DELETE FROM lead_estado
            WHERE email = ? AND url = ?
        """, (email, dominio))

        db.execute("""
            DELETE FROM lead_tarea
            WHERE email = ? AND dominio = ?
        """, (email, dominio))

        db.execute("""
            DELETE FROM lead_historial
            WHERE email = ? AND dominio = ?
        """, (email, dominio))

        db.commit()

def editar_tarea_existente(email: str, tarea_id: int, datos):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            UPDATE lead_tarea
            SET texto = ?, fecha = ?, prioridad = ?, tipo = ?, nicho = ?, dominio = ?
            WHERE email = ? AND id = ?
        """, (
            datos.texto,
            datos.fecha,
            datos.prioridad or "media",
            datos.tipo,
            datos.nicho,
            datos.dominio,
            email,
            tarea_id
        ))
        db.commit()

def editar_tarea_existente_postgres(email: str, tarea_id: int, datos, db: Session):
    tarea = db.query(LeadTarea).filter(
        LeadTarea.id == tarea_id,
        LeadTarea.user_email_lower == email
    ).first()

    if tarea:
        tarea.texto = datos.texto
        tarea.fecha = datos.fecha
        tarea.prioridad = datos.prioridad or "media"
        tarea.tipo = datos.tipo
        tarea.nicho = datos.nicho
        tarea.dominio = datos.dominio
        tarea.auto = datos.auto
        db.commit()

def obtener_historial_por_nicho(email: str, nicho: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT tipo, descripcion, timestamp
            FROM lead_historial
            WHERE email = ? AND tipo = 'nicho' AND dominio = ?
            ORDER BY timestamp DESC
        """, (email, nicho))
        rows = cursor.fetchall()
        return [{"tipo": row[0], "descripcion": row[1], "timestamp": row[2]} for row in rows]

def obtener_todos_los_dominios_usuario(email: str, db: Session):
    resultados = (
        db.query(LeadExtraido.url)
        .filter(LeadExtraido.user_email_lower == email)
        .distinct()
        .all()
    )
    return [row[0] for row in resultados]


def guardar_info_extra(user_email: str, dominio: str, email: str, telefono: str, informacion: str):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as db:
        cur = db.execute(
            "SELECT id FROM lead_info_extra WHERE user_email = ? AND dominio = ?",
            (user_email, dominio),
        )
        row = cur.fetchone()
        if row:
            db.execute(
                "UPDATE lead_info_extra SET email = ?, telefono = ?, informacion = ?, timestamp = ? WHERE id = ?",
                (email, telefono, informacion, timestamp, row[0]),
            )
        else:
            db.execute(
                "INSERT INTO lead_info_extra (dominio, email, telefono, informacion, user_email, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (dominio, email, telefono, informacion, user_email, timestamp),
            )
        db.commit()

from backend.models import LeadInfoExtra

def guardar_info_extra_postgres(user_email: str, dominio: str, email: str, telefono: str, informacion: str, db: Session):
    email_lower = (user_email or "").strip().lower()
    existente = db.query(LeadInfoExtra).filter_by(user_email_lower=email_lower, dominio=dominio).first()
    if existente:
        existente.email = email
        existente.telefono = telefono
        existente.informacion = informacion
    else:
        nuevo = LeadInfoExtra(
            dominio=dominio,
            email=email,
            telefono=telefono,
            informacion=informacion,
            user_email=user_email,
            user_email_lower=email_lower
        )
        db.add(nuevo)
    db.commit()


def obtener_info_extra(user_email: str, dominio: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("SELECT email, telefono, informacion FROM lead_info_extra WHERE user_email = ? AND dominio = ?", (user_email, dominio))
        row = cursor.fetchone()
        return {
            "email": row[0] if row else "",
            "telefono": row[1] if row else "",
            "informacion": row[2] if row else ""
        }
def obtener_info_extra_postgres(user_email: str, dominio: str, db: Session):
    email_lower = (user_email or "").strip().lower()
    info = db.query(LeadInfoExtra).filter_by(user_email_lower=email_lower, dominio=dominio).first()
    return {
        "email": info.email if info else "",
        "telefono": info.telefono if info else "",
        "informacion": info.informacion if info else ""
    }
