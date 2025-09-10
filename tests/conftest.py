import os, subprocess, pytest, importlib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

USE_TESTCONTAINERS = os.getenv("USE_TESTCONTAINERS", "1") != "0"

def run_alembic_upgrade(database_url: str):
    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    subprocess.check_call(["alembic", "upgrade", "head"], env=env)

@pytest.fixture(scope="session")
def pg_url():
    if USE_TESTCONTAINERS:
        try:
            from testcontainers.postgres import PostgresContainer
            with PostgresContainer("postgres:15") as pg:
                url = pg.get_connection_url()
                run_alembic_upgrade(url)
                yield url
                return
        except Exception:
            pass
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("No hay Postgres disponible (sin Docker y sin TEST_DATABASE_URL)")
    run_alembic_upgrade(url)
    yield url

@pytest.fixture(scope="function")
def db_session(pg_url):
    engine = create_engine(pg_url, future=True)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        yield s
        s.rollback()

@pytest.fixture(scope="function")
def client(pg_url):
    os.environ["DATABASE_URL"] = pg_url
    from backend import database as db_module
    importlib.reload(db_module)
    from backend import main as main_module
    importlib.reload(main_module)
    from fastapi.testclient import TestClient
    return TestClient(main_module.app)
