from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, LeadTarea


def test_insert_tarea_default_auto_false():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tarea = LeadTarea(
        email="a",
        user_email_lower="a",
        texto="t",
        timestamp="1",
    )
    session.add(tarea)
    session.commit()

    fetched = session.query(LeadTarea).first()
    assert fetched.auto is False
