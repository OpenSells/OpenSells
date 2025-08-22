from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

from sqlalchemy import func
import sqlite3
from datetime import datetime
from backend.utils import normalizar_dominio

DB_PATH = "backend/historial.db"

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
from sqlalchemy.orm import Session
from backend.models import LeadTarea

def guardar_tarea_lead_postgres(email: str, texto: str, fecha: str = None, dominio: str = None,
                                 tipo: str = "lead", nicho: str = None, prioridad: str = "media",
                                 db=None):
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
        prioridad=prioridad
    )
    db.add(nueva_tarea)
    db.commit()

def obtener_todas_tareas_pendientes_postgres(email: str, db: Session):
    tareas = (
        db.query(LeadTarea)
        .filter(LeadTarea.user_email_lower == email)
        .order_by(
            LeadTarea.completado.asc(),
            LeadTarea.prioridad.asc(),
            LeadTarea.fecha.is_(None),
            LeadTarea.fecha.asc(),
            LeadTarea.timestamp.desc()
        )
        .all()
    )

    resultado = []
    for t in tareas:
        resultado.append({
            "id": t.id,
            "dominio": t.dominio,
            "texto": t.texto,
            "fecha": t.fecha,
            "completado": t.completado,
            "timestamp": t.timestamp,
            "tipo": t.tipo,
            "nicho": t.nicho,
            "prioridad": t.prioridad,
        })

    return resultado

def obtener_tareas_lead_postgres(email: str, dominio: str, db: Session):
    resultados = (
        db.query(LeadTarea)
        .filter(LeadTarea.user_email_lower == email, LeadTarea.dominio == dominio)
        .order_by(LeadTarea.timestamp.desc())
        .all()
    )

    return [
        {
            "id": tarea.id,
            "texto": tarea.texto,
            "fecha": tarea.fecha,
            "completado": tarea.completado,
            "timestamp": tarea.timestamp,
            "tipo": tarea.tipo or "lead",
            "prioridad": tarea.prioridad or "media",
            "dominio": tarea.dominio
        }
        for tarea in resultados
    ]

def marcar_tarea_completada_postgres(email: str, tarea_id: int, db: Session):
    tarea = db.query(LeadTarea).filter(
        LeadTarea.id == tarea_id,
        LeadTarea.user_email_lower == email
    ).first()

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

from datetime import datetime
from sqlalchemy.orm import Session
from backend.models import LeadExtraido, Nicho, Suscripcion

def guardar_leads_extraidos(
    user_email: str, dominios: list[str], nicho: str, nicho_original: str, db: Session
):
    """Guardar una lista de dominios como leads extraídos.

    Lanza una excepción si ocurre algún error o si no se inserta ningún registro
    nuevo aun cuando se proporcionaron dominios.
    """

    user_email_lower = (user_email or "").strip().lower()
    nuevos = []

    # Ensure nicho exists
    nicho_row = (
        db.query(Nicho)
        .filter_by(user_email_lower=user_email_lower, nicho=nicho)
        .first()
    )
    if not nicho_row:
        nicho_row = Nicho(
            user_email_lower=user_email_lower,
            nicho=nicho,
            nicho_original=nicho_original,
        )
        db.add(nicho_row)

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
            )
            db.add(nuevo)
            nuevos.append(nuevo)

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
    resultados = (
        db.query(
            Nicho.nicho,
            Nicho.nicho_original,
            func.count(LeadExtraido.id).label("total_leads"),
        )
        .outerjoin(
            LeadExtraido,
            (LeadExtraido.user_email_lower == Nicho.user_email_lower)
            & (LeadExtraido.nicho == Nicho.nicho),
        )
        .filter(Nicho.user_email_lower == user_email)
        .group_by(Nicho.nicho, Nicho.nicho_original)
        .order_by(func.max(LeadExtraido.timestamp).desc())
        .all()
    )
    return [
        {
            "nicho": row.nicho,
            "nicho_original": row.nicho_original,
            "total_leads": row.total_leads,
        }
        for row in resultados
    ]

def obtener_leads_por_nicho(user_email: str, nicho: str, db: Session):
    resultados = (
        db.query(LeadExtraido)
        .filter(LeadExtraido.user_email_lower == user_email, LeadExtraido.nicho == nicho)
        .order_by(LeadExtraido.timestamp.desc())
        .all()
    )
    return [{"url": lead.url, "timestamp": lead.timestamp} for lead in resultados]

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
    db.query(Nicho).filter(
        Nicho.user_email_lower == user_email, Nicho.nicho == nicho
    ).delete(synchronize_session=False)
    db.commit()

def obtener_urls_extraidas_por_nicho(user_email: str, nicho: str, db: Session):
    resultados = (
        db.query(LeadExtraido.url)
        .filter(LeadExtraido.user_email_lower == user_email, LeadExtraido.nicho == nicho)
        .all()
    )
    return [row[0] for row in resultados]


def tiene_suscripcion_activa(email_lower: str, db: Session) -> bool:
    """Comprueba si el usuario tiene una suscripción activa."""
    now = datetime.utcnow()
    sus = (
        db.query(Suscripcion)
        .filter(
            Suscripcion.user_email_lower == email_lower,
            Suscripcion.status == "active",
            Suscripcion.current_period_end >= now,
        )
        .order_by(Suscripcion.current_period_end.desc())
        .first()
    )
    return sus is not None

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
    existente = db.query(LeadNota).filter_by(email_lower=email_lower, url=url).first()
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
    nota = db.query(LeadNota).filter_by(email_lower=email_lower, url=url).first()
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
            (LeadNota.url == LeadExtraido.url) & (LeadNota.email_lower == LeadExtraido.user_email_lower)
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
            "nicho": tarea.nicho
        }
    return None



def guardar_memoria_usuario(email: str, descripcion: str):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS usuario_memoria (
                email TEXT PRIMARY KEY,
                descripcion TEXT,
                timestamp TEXT
            )
        """)
        db.execute("""
            INSERT INTO usuario_memoria (email, descripcion, timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                descripcion = excluded.descripcion,
                timestamp = excluded.timestamp
        """, (email, descripcion, timestamp))
        db.commit()

def obtener_memoria_usuario(email: str) -> str:
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS usuario_memoria (
                email TEXT PRIMARY KEY,
                descripcion TEXT,
                timestamp TEXT
            )
        """)
        cursor = db.execute("SELECT descripcion FROM usuario_memoria WHERE email = ?", (email,))
        row = cursor.fetchone()
        return row[0] if row else ""

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

def mover_lead_en_bd(user_email: str, dominio_original: str, nicho_origen: str, nicho_destino: str, nicho_original_destino: str, db: Session):
    from backend.models import LeadExtraido, LeadTarea

    dominio_limpio = normalizar_dominio(dominio_original)

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


def editar_nombre_nicho(email: str, nicho_actual: str, nuevo_nombre: str):
    from backend.utils import normalizar_nicho
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
