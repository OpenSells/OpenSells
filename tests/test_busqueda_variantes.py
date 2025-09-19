def _main_module():
    from backend import main as main_module

    return main_module


def _token(client):
    email = "busqueda@example.com"
    password = "secret"
    client.post("/register", json={"email": email, "password": password})
    r = client.post("/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_buscar_variantes_includes_extended_metadata(client):
    main_module = _main_module()
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/buscar",
        json={"cliente_ideal": "clinicas veterinarias en madrid"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["has_extended_variant"] is True
    assert data["extended_index"] == len(data["variantes"]) - 1
    assert data["variantes_display"][data["extended_index"]].startswith(main_module.EXTENDED_PREFIX)
    assert len(data["variantes_display"]) == len(data["variantes"])


def test_build_variantes_display_without_extended(client):
    main_module = _main_module()
    variantes = ["uno", "dos", "tres"]
    display, has_extended, idx = main_module.build_variantes_display(variantes)

    assert display == variantes
    assert has_extended is False
    assert idx is None


def test_normalize_client_variantes_strips_prefix_but_keeps_operators(client):
    main_module = _main_module()
    variantes_display = [f"{main_module.EXTENDED_PREFIX}clinicas veterinarias -site:yelp.es"]
    normalizadas = main_module.normalize_client_variantes(variantes_display)

    assert normalizadas == ["clinicas veterinarias -site:yelp.es"]
    assert "-site:" in normalizadas[0]
