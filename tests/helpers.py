def auth(client, email):
    password = "pw"
    client.post("/register", json={"email": email, "password": password})
    token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def set_plan(db_session, email, plan):
    from backend.models import Usuario

    u = db_session.query(Usuario).filter_by(email=email.lower()).first()
    u.plan = plan
    db_session.commit()
