from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
    func,
    text,
    UniqueConstraint,
)
from sqlalchemy.orm import validates
from backend.database import Base
import enum
import os


class LeadEstadoContacto(enum.Enum):
    pendiente = "pendiente"
    en_proceso = "en_proceso"
    contactado = "contactado"

# Tabla de usuarios
class Usuario(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    plan = Column(String, default="free")
    suspendido = Column(Boolean, default=False)

# Tabla de tareas
class LeadTarea(Base):
    __tablename__ = "lead_tarea"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    user_email_lower = Column(String, index=True, nullable=False)
    dominio = Column(String)
    texto = Column(Text, nullable=False)
    fecha = Column(String)
    completado = Column(Boolean, default=False)
    timestamp = Column(String)
    tipo = Column(String, default="lead")
    nicho = Column(String)
    prioridad = Column(String, default="media")
    auto = Column(Boolean, nullable=False, server_default=text("false"))

    @validates("email")
    def _set_lower(self, key, value):
        self.user_email_lower = (value or "").strip().lower()
        return (value or "").strip()

# Tabla de historial
class LeadHistorial(Base):
    __tablename__ = "lead_historial"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    user_email_lower = Column(String, index=True, nullable=False)
    dominio = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    @validates("email")
    def _set_lower(self, key, value):
        self.user_email_lower = (value or "").strip().lower()
        return (value or "").strip()


class LeadNota(Base):
    __tablename__ = "lead_nota"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    user_email_lower = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    nota = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    @validates("email")
    def _set_lower(self, key, value):
        self.user_email_lower = (value or "").strip().lower()
        return (value or "").strip()

class LeadInfoExtra(Base):
    __tablename__ = "lead_info_extra"

    id = Column(Integer, primary_key=True)
    dominio = Column(String, nullable=False)
    email = Column(String)
    telefono = Column(String)
    informacion = Column(Text)
    user_email = Column(String)
    user_email_lower = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    @validates("user_email")
    def _set_lower(self, key, value):
        self.user_email_lower = (value or "").strip().lower()
        return (value or "").strip()

class LeadExtraido(Base):
    __tablename__ = "leads_extraidos"

    id = Column(Integer, primary_key=True)
    user_email = Column(String, nullable=False)
    user_email_lower = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    nicho = Column(String, nullable=False)  # Normalizado
    nicho_original = Column(String, nullable=False)
    estado_contacto = Column(String(20), nullable=False, server_default="pendiente", index=True)

    @validates("user_email")
    def _set_lower(self, key, value):
        self.user_email_lower = (value or "").strip().lower()
        return (value or "").strip()


# Memoria de usuario almacenada en PostgreSQL
class UsuarioMemoria(Base):
    __tablename__ = "usuario_memoria"

    email_lower = Column(String, primary_key=True, index=True)
    descripcion = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


FEATURE_NEW_MODELS = os.getenv("FEATURE_NEW_MODELS", "false").lower() == "true"


if FEATURE_NEW_MODELS:
    class UserUsageMonthly(Base):
        __tablename__ = "user_usage_monthly"
        __table_args__ = (
            UniqueConstraint("user_id", "period_yyyymm", name="uix_user_period"),
        )

        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, index=True, nullable=False)
        period_yyyymm = Column(String, nullable=False)
        leads = Column(Integer, default=0)
        ia_msgs = Column(Integer, default=0)
        tasks = Column(Integer, default=0)
        csv_exports = Column(Integer, default=0)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        )
