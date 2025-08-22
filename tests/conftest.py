import os

# Provide default environment variables for tests
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("ALLOW_ANON_USER", "1")
