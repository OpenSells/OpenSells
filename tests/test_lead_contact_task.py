import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, LeadExtraido, LeadTarea
from backend.db import guardar_leads_extraidos


def test_guardar_lead_crea_estado_y_tarea():
    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    guardar_leads_extraidos("test@example.com", ["example.com"], "nicho", "Nicho", session)

    lead = session.query(LeadExtraido).first()
    assert lead is not None
    assert lead.estado_contacto == "pendiente"

    tarea = session.query(LeadTarea).first()
    assert tarea is not None
    assert tarea.auto is True
    assert tarea.completado is False

