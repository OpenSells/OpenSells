def test_http_exception_normalized(client):
    r = client.get("/no-such-endpoint")
    assert r.status_code == 404
    assert r.json() == {"detail": {"code": "HTTP_ERROR", "message": "Not Found"}}


def test_validation_error_normalized(client):
    r = client.post("/register", json={})
    assert r.status_code == 422
    assert r.json() == {
        "detail": {
            "code": "VALIDATION_ERROR",
            "message": "Solicitud inválida. Revisa los campos enviados.",
        }
    }
