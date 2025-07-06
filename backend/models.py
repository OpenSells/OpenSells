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
