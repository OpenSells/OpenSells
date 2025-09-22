from backend.database import Base, engine
from backend.models import (
    Usuario,
    LeadTarea,
    LeadHistorial,
    LeadNota,
    LeadInfoExtra,
    LeadExtraido,
    LeadEstado,
    UsuarioMemoria,
)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente.")
