import sqlite3
from datetime import datetime

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
            email TEXT NOT NULL,
            dominio TEXT NOT NULL,
            email_contacto TEXT,
            telefono TEXT,
            info_adicional TEXT,
            timestamp TEXT,
            PRIMARY KEY (email, dominio)
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

def obtener_tareas_lead_postgres(email: str, dominio: str, db: Session):
    resultados = (
        db.query(LeadTarea)
        .filter(LeadTarea.email == email, LeadTarea.dominio == dominio)
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

def marcar_tarea_completada(email: str, tarea_id: int):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            UPDATE lead_tarea
            SET completado = 1
            WHERE email = ? AND id = ?
        """, (email, tarea_id))
        db.commit()

def guardar_exportacion(user_email: str, filename: str):
    with sqlite3.connect(DB_PATH) as db:
        timestamp = datetime.utcnow().isoformat()
        db.execute(
            "INSERT INTO historial (user_email, filename, timestamp) VALUES (?, ?, ?)",
            (user_email, filename, timestamp)
        )
        db.commit()

def guardar_leads_extraidos(user_email: str, dominios: list[str], nicho: str, nicho_original: str):
    from urllib.parse import urlparse
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as db:
        for dominio in dominios:
            # Sanear dominio en caso de que venga como URL
            try:
                netloc = urlparse(dominio).netloc
                dominio_limpio = netloc.replace("www.", "").strip() if netloc else dominio.replace("www.", "").strip()
            except:
                dominio_limpio = dominio
            db.execute("""
                INSERT INTO leads_extraidos (user_email, url, timestamp, nicho, nicho_original)
                VALUES (?, ?, ?, ?, ?)
            """, (user_email, dominio_limpio, timestamp, nicho, nicho_original))
        db.commit()

def obtener_historial(user_email: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT filename, timestamp FROM historial
            WHERE user_email = ?
            ORDER BY timestamp DESC
        """, (user_email,))
        rows = cursor.fetchall()
        return [{"filename": row[0], "timestamp": row[1]} for row in rows]

def obtener_nichos_usuario(user_email: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT nicho, MAX(nicho_original) FROM leads_extraidos
            WHERE user_email = ?
            GROUP BY nicho
            ORDER BY MAX(timestamp) DESC
        """, (user_email,))
        rows = cursor.fetchall()
        return [{"nicho": row[0], "nicho_original": row[1]} for row in rows]

def obtener_leads_por_nicho(user_email: str, nicho: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT url, timestamp FROM leads_extraidos
            WHERE user_email = ? AND nicho = ?
            ORDER BY timestamp DESC
        """, (user_email, nicho))
        rows = cursor.fetchall()
        return [{"url": row[0], "timestamp": row[1]} for row in rows]

def eliminar_nicho(user_email: str, nicho: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND nicho = ?
        """, (user_email, nicho))
        db.commit()

def obtener_urls_extraidas_por_nicho(user_email: str, nicho: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT url FROM leads_extraidos
            WHERE user_email = ? AND nicho = ?
        """, (user_email, nicho))
        rows = cursor.fetchall()
        return [row[0] for row in rows]

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

def obtener_nota_lead(email: str, url: str) -> str:
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT nota FROM lead_nota
            WHERE email = ? AND url = ?
        """, (email, url))
        row = cursor.fetchone()
        return row[0] if row else ""

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

def obtener_tarea_por_id(email: str, tarea_id: int):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT id, dominio, texto, tipo, nicho
            FROM lead_tarea
            WHERE email = ? AND id = ?
        """, (email, tarea_id))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "dominio": row[1],
                "texto": row[2],
                "tipo": row[3],
                "nicho": row[4]
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

def eliminar_lead_de_nicho(user_email: str, dominio: str, nicho: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND url = ? AND nicho = ?
        """, (user_email, dominio, nicho))
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

def mover_lead_en_bd(user_email: str, dominio_original: str, nicho_origen: str, nicho_destino: str, nicho_original_destino: str):
    dominio_limpio = extraer_dominio_base(dominio_original)
    with sqlite3.connect(DB_PATH) as db:
        # 🗑️ Borrar de leads_extraidos (tabla de leads)
        db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND url = ? AND nicho = ?
        """, (user_email, dominio_limpio, nicho_origen))

        # ✅ Insertar en leads_extraidos con nuevo nicho
        timestamp = datetime.utcnow().isoformat()
        db.execute("""
            INSERT INTO leads_extraidos (user_email, url, timestamp, nicho, nicho_original)
            VALUES (?, ?, ?, ?, ?)
        """, (user_email, dominio_limpio, timestamp, nicho_destino, nicho_original_destino))

        # 🔁 Actualizar todas las tareas que correspondan a este dominio
        db.execute("""
            UPDATE lead_tarea
            SET nicho = ?
            WHERE email = ? AND dominio = ?
        """, (nicho_destino, user_email, dominio_limpio))

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

def obtener_todos_los_dominios_usuario(email: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT DISTINCT url FROM leads_extraidos
            WHERE user_email = ?
        """, (email,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]


def guardar_info_extra(email: str, dominio: str, email_contacto: str, telefono: str, info_adicional: str):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            INSERT INTO lead_info_extra (email, dominio, email_contacto, telefono, info_adicional, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email, dominio) DO UPDATE SET
                email_contacto = excluded.email_contacto,
                telefono = excluded.telefono,
                info_adicional = excluded.info_adicional,
                timestamp = excluded.timestamp
        """, (email, dominio, email_contacto, telefono, info_adicional, timestamp))
        db.commit()


def obtener_info_extra(email: str, dominio: str):
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute("""
            SELECT email_contacto, telefono, info_adicional
            FROM lead_info_extra
            WHERE email = ? AND dominio = ?
        """, (email, dominio))
        row = cursor.fetchone()
        return {
            "email_contacto": row[0] if row else "",
            "telefono": row[1] if row else "",
            "info_adicional": row[2] if row else ""
        }
