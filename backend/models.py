from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, func
from backend.database import Base

# Tabla de usuarios
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    plan = Column(String, default="free")

# Tabla de tareas
class LeadTarea(Base):
    __tablename__ = "lead_tarea"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    dominio = Column(String)
    texto = Column(Text, nullable=False)
    fecha = Column(String)
    completado = Column(Boolean, default=False)
    timestamp = Column(String)
    tipo = Column(String, default="lead")
    nicho = Column(String)
    prioridad = Column(String, default="media")

# Tabla de historial
class LeadHistorial(Base):
    __tablename__ = "lead_historial"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    dominio = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class LeadNota(Base):
    __tablename__ = "lead_nota"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    url = Column(String, nullable=False)
    nota = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class LeadInfoExtra(Base):
    __tablename__ = "lead_info_extra"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    dominio = Column(String, nullable=False)
    email_contacto = Column(String)
    telefono = Column(String)
    info_adicional = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class LeadExtraido(Base):
    __tablename__ = "leads_extraidos"

    id = Column(Integer, primary_key=True)
    user_email = Column(String, nullable=False)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    nicho = Column(String, nullable=False)  # Normalizado
    nicho_original = Column(String, nullable=False)
