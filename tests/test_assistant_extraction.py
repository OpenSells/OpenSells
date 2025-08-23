import os
import importlib
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_backend_blocks_assistant(monkeypatch):
    monkeypatch.setenv("ASSISTANT_EXTRACTION_ENABLED", "false")
    import backend.main as main
    importlib.reload(main)
    client = TestClient(main.app)
    resp = client.post("/buscar", json={"cliente_ideal": "dentistas"}, headers={"X-Client-Source": "assistant"})
    assert resp.status_code == 200
    assert resp.json()["detail"] == "assistant_extraction_placeholder"


def test_backend_allows_when_enabled(monkeypatch):
    monkeypatch.setenv("ASSISTANT_EXTRACTION_ENABLED", "true")
    import backend.main as main
    import importlib
    import types

    importlib.reload(main)

    def dummy_create(*args, **kwargs):
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="- v1"))])

    main.openai_client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=dummy_create)))
    client = TestClient(main.app)
    resp = client.post("/buscar", json={"cliente_ideal": "dentistas"})
    assert resp.status_code == 200


def test_frontend_api_buscar_guard(monkeypatch):
    monkeypatch.setenv("ASSISTANT_EXTRACTION_ENABLED", "false")
    import streamlit_app.assistant_api as assistant_api
    importlib.reload(assistant_api)
    post_mock = MagicMock()
    monkeypatch.setattr(assistant_api.http_client, "post", post_mock)
    result = assistant_api.api_buscar("dentistas")
    assert result == {"error": assistant_api.EXTRAER_LEADS_MSG}
    post_mock.assert_not_called()
