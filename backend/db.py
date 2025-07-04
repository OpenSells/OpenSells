import aiosqlite
from datetime import datetime

DB_PATH = "backend/historial.db"

async def crear_tablas_si_no_existen():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            filename TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        await db.execute("""
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
        await db.execute("""
        CREATE TABLE IF NOT EXISTS lead_historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            dominio TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        await db.execute("""
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
        await db.commit()

async def guardar_tarea_lead(email: str, texto: str, fecha: str = None, dominio: str = None,
                              tipo: str = "lead", nicho: str = None, prioridad: str = "media"):
    timestamp = datetime.utcnow().isoformat()
    completado = 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO lead_tarea (email, dominio, texto, fecha, completado, timestamp, tipo, nicho, prioridad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, dominio, texto, fecha, completado, timestamp, tipo, nicho, prioridad))
        await db.commit()

async def obtener_tareas_lead(email: str, dominio: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, texto, fecha, completado, timestamp, tipo, prioridad, dominio
            FROM lead_tarea
            WHERE email = ? AND dominio = ?
            ORDER BY timestamp DESC
        """, (email, dominio))
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "texto": row[1],
                "fecha": row[2],
                "completado": bool(row[3]),
                "timestamp": row[4],
                "tipo": row[5] or "lead",
                "prioridad": row[6] or "media",
                "dominio": row[7]
            } for row in rows
        ]

async def marcar_tarea_completada(email: str, tarea_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE lead_tarea
            SET completado = 1
            WHERE email = ? AND id = ?
        """, (email, tarea_id))
        await db.commit()

async def guardar_exportacion(user_email: str, filename: str):
    async with aiosqlite.connect(DB_PATH) as db:
        timestamp = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO historial (user_email, filename, timestamp) VALUES (?, ?, ?)",
            (user_email, filename, timestamp)
        )
        await db.commit()

async def guardar_leads_extraidos(user_email: str, dominios: list[str], nicho: str, nicho_original: str):
    from urllib.parse import urlparse
    timestamp = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for dominio in dominios:
            # Sanear dominio en caso de que venga como URL
            try:
                netloc = urlparse(dominio).netloc
                dominio_limpio = netloc.replace("www.", "").strip() if netloc else dominio.replace("www.", "").strip()
            except:
                dominio_limpio = dominio
            await db.execute("""
                INSERT INTO leads_extraidos (user_email, url, timestamp, nicho, nicho_original)
                VALUES (?, ?, ?, ?, ?)
            """, (user_email, dominio_limpio, timestamp, nicho, nicho_original))
        await db.commit()

async def obtener_historial(user_email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT filename, timestamp FROM historial
            WHERE user_email = ?
            ORDER BY timestamp DESC
        """, (user_email,))
        rows = await cursor.fetchall()
        return [{"filename": row[0], "timestamp": row[1]} for row in rows]

async def obtener_nichos_usuario(user_email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT nicho, MAX(nicho_original) FROM leads_extraidos
            WHERE user_email = ?
            GROUP BY nicho
            ORDER BY MAX(timestamp) DESC
        """, (user_email,))
        rows = await cursor.fetchall()
        return [{"nicho": row[0], "nicho_original": row[1]} for row in rows]

async def obtener_leads_por_nicho(user_email: str, nicho: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT url, timestamp FROM leads_extraidos
            WHERE user_email = ? AND nicho = ?
            ORDER BY timestamp DESC
        """, (user_email, nicho))
        rows = await cursor.fetchall()
        return [{"url": row[0], "timestamp": row[1]} for row in rows]

async def eliminar_nicho(user_email: str, nicho: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND nicho = ?
        """, (user_email, nicho))
        await db.commit()

async def obtener_urls_extraidas_por_nicho(user_email: str, nicho: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT url FROM leads_extraidos
            WHERE user_email = ? AND nicho = ?
        """, (user_email, nicho))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def guardar_estado_lead(email: str, url: str, estado: str):
    timestamp = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO lead_estado (email, url, estado, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email, url) DO UPDATE SET
                estado = excluded.estado,
                timestamp = excluded.timestamp
        """, (email, url, estado, timestamp))
        await db.commit()

async def obtener_estado_lead(email: str, url: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT estado FROM lead_estado
            WHERE email = ? AND url = ?
        """, (email, url))
        row = await cursor.fetchone()
        return row[0] if row else None

async def obtener_nichos_para_url(user_email: str, url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT DISTINCT nicho_original FROM leads_extraidos
            WHERE user_email = ? AND url = ?
        """, (user_email, url))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def guardar_nota_lead(email: str, url: str, nota: str):
    timestamp = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO lead_nota (email, url, nota, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email, url) DO UPDATE SET
                nota = excluded.nota,
                timestamp = excluded.timestamp
        """, (email, url, nota, timestamp))
        await db.commit()

async def obtener_nota_lead(email: str, url: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT nota FROM lead_nota
            WHERE email = ? AND url = ?
        """, (email, url))
        row = await cursor.fetchone()
        return row[0] if row else ""

async def buscar_leads_global(email: str, query: str):
    query = f"%{query.lower()}%"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
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
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def obtener_tareas_pendientes(email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
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
        rows = await cursor.fetchall()
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

async def obtener_todas_tareas_pendientes(email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
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
        rows = await cursor.fetchall()
        col_names = [column[0] for column in cursor.description]
        tareas = [dict(zip(col_names, row)) for row in rows]

        # Añadir nota a cada tarea si existe
        for tarea in tareas:
            dominio = tarea.get("dominio")
            if dominio:  # solo buscar nota si hay dominio
                nota_cursor = await db.execute("""
                    SELECT nota FROM lead_nota WHERE email = ? AND url = ?
                """, (email, dominio))
                nota_row = await nota_cursor.fetchone()
                if nota_row:
                    tarea["nota"] = nota_row[0]

        return tareas

async def guardar_evento_historial(email: str, dominio: str, tipo: str, descripcion: str):
    timestamp = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO lead_historial (email, dominio, tipo, descripcion, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (email, dominio, tipo, descripcion, timestamp))
        await db.commit()

async def obtener_historial_por_dominio(email: str, dominio: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT tipo, descripcion, timestamp
            FROM lead_historial
            WHERE email = ? AND dominio = ?
            ORDER BY timestamp DESC
        """, (email, dominio))
        rows = await cursor.fetchall()
        return [
            {"tipo": row[0], "descripcion": row[1], "timestamp": row[2]}
            for row in rows
        ]

async def obtener_tarea_por_id(email: str, tarea_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, dominio, texto, tipo, nicho
            FROM lead_tarea
            WHERE email = ? AND id = ?
        """, (email, tarea_id))
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "dominio": row[1],
                "texto": row[2],
                "tipo": row[3],
                "nicho": row[4]
            }
        return None

async def guardar_memoria_usuario(email: str, descripcion: str):
    timestamp = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usuario_memoria (
                email TEXT PRIMARY KEY,
                descripcion TEXT,
                timestamp TEXT
            )
        """)
        await db.execute("""
            INSERT INTO usuario_memoria (email, descripcion, timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                descripcion = excluded.descripcion,
                timestamp = excluded.timestamp
        """, (email, descripcion, timestamp))
        await db.commit()

async def obtener_memoria_usuario(email: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usuario_memoria (
                email TEXT PRIMARY KEY,
                descripcion TEXT,
                timestamp TEXT
            )
        """)
        cursor = await db.execute("SELECT descripcion FROM usuario_memoria WHERE email = ?", (email,))
        row = await cursor.fetchone()
        return row[0] if row else ""

async def obtener_historial_por_tipo(email: str, tipo: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT tipo, descripcion, timestamp
            FROM lead_historial
            WHERE email = ? AND tipo = ?
            ORDER BY timestamp DESC
        """, (email, tipo))
        rows = await cursor.fetchall()
        return [{"tipo": row[0], "descripcion": row[1], "timestamp": row[2]} for row in rows]

async def eliminar_lead_de_nicho(user_email: str, dominio: str, nicho: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND url = ? AND nicho = ?
        """, (user_email, dominio, nicho))
        await db.commit()

from urllib.parse import urlparse

def extraer_dominio_base(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        dominio = urlparse(url).netloc
        return dominio.replace("www.", "").strip()
    else:
        return url.replace("www.", "").strip()

async def mover_lead_en_bd(user_email: str, dominio_original: str, nicho_origen: str, nicho_destino: str, nicho_original_destino: str):
    dominio_limpio = extraer_dominio_base(dominio_original)
    async with aiosqlite.connect(DB_PATH) as db:
        # 🗑️ Borrar de leads_extraidos (tabla de leads)
        await db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND url = ? AND nicho = ?
        """, (user_email, dominio_limpio, nicho_origen))

        # ✅ Insertar en leads_extraidos con nuevo nicho
        timestamp = datetime.utcnow().isoformat()
        await db.execute("""
            INSERT INTO leads_extraidos (user_email, url, timestamp, nicho, nicho_original)
            VALUES (?, ?, ?, ?, ?)
        """, (user_email, dominio_limpio, timestamp, nicho_destino, nicho_original_destino))

        # 🔁 Actualizar todas las tareas que correspondan a este dominio
        await db.execute("""
            UPDATE lead_tarea
            SET nicho = ?
            WHERE email = ? AND dominio = ?
        """, (nicho_destino, user_email, dominio_limpio))

        await db.commit()

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

async def editar_nombre_nicho(email: str, nicho_actual: str, nuevo_nombre: str):
    from .main import normalizar_nicho
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE leads_extraidos
            SET nicho_original = ?, nicho = ?
            WHERE user_email = ? AND nicho = ?
        """, (nuevo_nombre, normalizar_nicho(nuevo_nombre), email, normalizar_nicho(nicho_actual)))
        await db.commit()

async def eliminar_lead_completamente(email: str, dominio: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM leads_extraidos
            WHERE user_email = ? AND url = ?
        """, (email, dominio))

        await db.execute("""
            DELETE FROM lead_nota
            WHERE email = ? AND url = ?
        """, (email, dominio))

        await db.execute("""
            DELETE FROM lead_estado
            WHERE email = ? AND url = ?
        """, (email, dominio))

        await db.execute("""
            DELETE FROM lead_tarea
            WHERE email = ? AND dominio = ?
        """, (email, dominio))

        await db.execute("""
            DELETE FROM lead_historial
            WHERE email = ? AND dominio = ?
        """, (email, dominio))

        await db.commit()

async def editar_tarea_existente(email: str, tarea_id: int, datos):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
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
        await db.commit()

async def obtener_historial_por_nicho(email: str, nicho: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT tipo, descripcion, timestamp
            FROM lead_historial
            WHERE email = ? AND tipo = 'nicho' AND dominio = ?
            ORDER BY timestamp DESC
        """, (email, nicho))
        rows = await cursor.fetchall()
        return [{"tipo": row[0], "descripcion": row[1], "timestamp": row[2]} for row in rows]

async def obtener_todos_los_dominios_usuario(email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT DISTINCT url FROM leads_extraidos
            WHERE user_email = ?
        """, (email,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def guardar_info_extra(email: str, dominio: str, email_contacto: str, telefono: str, info_adicional: str):
    timestamp = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO lead_info_extra (email, dominio, email_contacto, telefono, info_adicional, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email, dominio) DO UPDATE SET
                email_contacto = excluded.email_contacto,
                telefono = excluded.telefono,
                info_adicional = excluded.info_adicional,
                timestamp = excluded.timestamp
        """, (email, dominio, email_contacto, telefono, info_adicional, timestamp))
        await db.commit()


async def obtener_info_extra(email: str, dominio: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT email_contacto, telefono, info_adicional
            FROM lead_info_extra
            WHERE email = ? AND dominio = ?
        """, (email, dominio))
        row = await cursor.fetchone()
        return {
            "email_contacto": row[0] if row else "",
            "telefono": row[1] if row else "",
            "info_adicional": row[2] if row else ""
        }
