from sqlalchemy import text
from backend.database import engine

TABLE_COLUMNS = {
    "lead_extraido": "user_email",
    "lead_tarea": "email",
    "lead_historial": "email",
    "lead_nota": "email",
    "lead_info_extra": "user_email",
}

def main():
    with engine.begin() as conn:
        for table, column in TABLE_COLUMNS.items():
            conn.execute(text(f"UPDATE {table} SET {column} = LOWER({column})"))

if __name__ == "__main__":
    main()
