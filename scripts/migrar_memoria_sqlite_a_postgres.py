#!/usr/bin/env python3
"""Migra los datos de usuario_memoria desde SQLite a PostgreSQL."""

import argparse
import os
import sqlite3
from pathlib import Path

# Asegurar que el backend esté en el PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.append(str(ROOT))

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database import SessionLocal, engine
from backend.models import UsuarioMemoria

SQLITE_PATH = ROOT / "backend" / "historial.db"


def migrar(dry_run: bool = False) -> None:
    if not SQLITE_PATH.exists():
        print(f"No se encontró {SQLITE_PATH}")
        return

    with sqlite3.connect(SQLITE_PATH) as src:
        try:
            rows = src.execute("SELECT email, descripcion FROM usuario_memoria").fetchall()
        except sqlite3.Error as exc:
            print(f"Error leyendo SQLite: {exc}")
            return

    inserted = updated = 0
    insert_fn = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert

    with SessionLocal() as db:
        for email, descripcion in rows:
            email_lower = (email or "").strip().lower()
            stmt = (
                insert_fn(UsuarioMemoria)
                .values(email_lower=email_lower, descripcion=descripcion, updated_at=func.now())
                .on_conflict_do_update(
                    index_elements=[UsuarioMemoria.email_lower],
                    set_={"descripcion": descripcion, "updated_at": func.now()},
                )
            )
            exists = db.get(UsuarioMemoria, email_lower) is not None
            if dry_run:
                if exists:
                    updated += 1
                else:
                    inserted += 1
                continue
            db.execute(stmt)
            if exists:
                updated += 1
            else:
                inserted += 1
        if not dry_run:
            db.commit()
    print(
        f"Filas procesadas: {len(rows)}. Insertadas: {inserted}. Actualizadas: {updated}. Dry-run={dry_run}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrar memorias de usuarios de SQLite a PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en la base de datos")
    args = parser.parse_args()
    migrar(dry_run=args.dry_run)
