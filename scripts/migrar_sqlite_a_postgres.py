#!/usr/bin/env python3
"""Migra datos de historial y lead_estado desde SQLite a PostgreSQL."""

import argparse
import sqlite3
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database import SessionLocal, engine
from backend.models import HistorialExport, LeadEstado

SQLITE_PATH = ROOT / "backend" / "historial.db"


def normalizar_dominio(dominio: str) -> str:
    if dominio.startswith("http://") or dominio.startswith("https://"):
        dominio = urlparse(dominio).netloc
    return dominio.replace("www.", "").strip().lower()


def migrar(drop: bool = False) -> None:
    if not SQLITE_PATH.exists():
        print(f"No se encontró {SQLITE_PATH}")
        return

    with sqlite3.connect(SQLITE_PATH) as src:
        cur = src.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='historial'"
        )
        hist_rows = (
            src.execute("SELECT user_email, filename, timestamp FROM historial").fetchall()
            if cur.fetchone()
            else []
        )
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='lead_estado'"
        )
        estado_rows = (
            src.execute("SELECT email, url, estado, timestamp FROM lead_estado").fetchall()
            if cur.fetchone()
            else []
        )

    insert_fn = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert
    with SessionLocal() as db:
        for email, filename, ts in hist_rows:
            stmt = insert_fn(HistorialExport).values(
                user_email=(email or "").strip().lower(),
                filename=filename,
                timestamp=ts,
            )
            db.execute(stmt)
        for email, url, estado, ts in estado_rows:
            email_lower = (email or "").strip().lower()
            dominio = normalizar_dominio(url or "")
            stmt = (
                insert_fn(LeadEstado)
                .values(
                    user_email_lower=email_lower,
                    dominio=dominio,
                    estado=estado,
                    timestamp=ts,
                )
                .on_conflict_do_update(
                    index_elements=[LeadEstado.user_email_lower, LeadEstado.dominio],
                    set_={"estado": estado, "timestamp": ts},
                )
            )
            db.execute(stmt)
        db.commit()
    print(
        f"Historial migrado: {len(hist_rows)} filas. Lead_estado migrado: {len(estado_rows)} filas."
    )
    if drop:
        with sqlite3.connect(SQLITE_PATH) as src:
            cur = src.cursor()
            for table in ("usuario_memoria", "historial", "lead_estado"):
                cur.execute(f"DROP TABLE IF EXISTS {table}")
            src.commit()
        print("Tablas SQLite eliminadas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrar datos de SQLite a PostgreSQL")
    parser.add_argument("--drop", action="store_true", help="Eliminar tablas SQLite tras migrar")
    args = parser.parse_args()
    migrar(drop=args.drop)
