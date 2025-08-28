from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, LeadExtraido


def test_estado_contacto_default():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    lead = LeadExtraido(
        user_email="a",
        user_email_lower="a",
        url="b",
        nicho="n",
        nicho_original="n",
    )
    session.add(lead)
    session.commit()

    fetched = session.query(LeadExtraido).first()
    assert fetched.estado_contacto == "pendiente"
