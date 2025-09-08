import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from backend.database import Base
from backend.models import Usuario
from backend.core.plans import PLANES
from backend.core.usage import check_and_inc, get_or_create_usage, get_period


def setup_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSession()


def create_user(session, plan="free"):
    user = Usuario(email="test@example.com", hashed_password="x", plan=plan)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_leads_limits():
    session = setup_session()
    user = create_user(session, plan="free")
    period = get_period()
    usage = get_or_create_usage(session, user.id, period)
    usage.leads = PLANES["free"].leads_mensuales
    session.add(usage)
    session.commit()
    with pytest.raises(HTTPException):
        check_and_inc(user, "leads", session)

    user.plan = "basico"
    usage.leads = PLANES["basico"].leads_mensuales
    session.add_all([user, usage])
    session.commit()
    with pytest.raises(HTTPException):
        check_and_inc(user, "leads", session)

    user.plan = "premium"
    usage.leads = PLANES["premium"].leads_mensuales
    session.add_all([user, usage])
    session.commit()
    with pytest.raises(HTTPException):
        check_and_inc(user, "leads", session)


def test_ia_message_limits():
    session = setup_session()
    user = create_user(session, plan="free")
    period = get_period()
    usage = get_or_create_usage(session, user.id, period)
    usage.ia_msgs = PLANES["free"].ia_mensajes
    session.add(usage)
    session.commit()
    with pytest.raises(HTTPException):
        check_and_inc(user, "ia_msgs", session)

    user.plan = "basico"
    usage.ia_msgs = PLANES["basico"].ia_mensajes
    session.add_all([user, usage])
    session.commit()
    with pytest.raises(HTTPException):
        check_and_inc(user, "ia_msgs", session)


def test_task_limits_and_unlimited():
    session = setup_session()
    user = create_user(session, plan="free")
    period = get_period()
    usage = get_or_create_usage(session, user.id, period)
    usage.tasks = PLANES["free"].tareas_max
    session.add(usage)
    session.commit()
    with pytest.raises(HTTPException):
        check_and_inc(user, "tasks", session)

    user.plan = "basico"
    usage.tasks = 1000
    session.add_all([user, usage])
    session.commit()
    # Should not raise for unlimited
    check_and_inc(user, "tasks", session)


def test_csv_blocked_for_free():
    session = setup_session()
    user = create_user(session, plan="free")
    with pytest.raises(HTTPException):
        check_and_inc(user, "csv_exports", session)

    user.plan = "basico"
    session.add(user)
    session.commit()
    # Should not raise for paid plan
    check_and_inc(user, "csv_exports", session)
