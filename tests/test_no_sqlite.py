import pathlib
import subprocess

def test_no_sqlite_references():
    repo = pathlib.Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            "rg",
            "-n",
            "(sqlite://|historial\\.db|aiosqlite)",
            str(repo),
            "-g",
            "!scripts/migrar_sqlite_a_postgres.py",
            "-g",
            "!scripts/migrar_memoria_sqlite_a_postgres.py",
            "-g",
            "!tests/**",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, f"Se encontraron referencias a SQLite:\n{result.stdout}"
