import os

# Provide default environment variables for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("ALLOW_ANON_USER", "1")

from backend.database import Base, engine
from backend import models  # register models

# Ensure tables exist for tests using global TestClient instances
Base.metadata.create_all(bind=engine)
