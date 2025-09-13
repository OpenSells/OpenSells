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
    Index,
)
from sqlalchemy.orm import validates
from backend.database import Base
import enum


class LeadEstadoContacto(enum.Enum):
    pendiente = "pendiente"
    en_proceso = "en_proceso"
    contactado = "contactado"

# Tabla de usuarios
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    plan = Column(String, default="free")
    suspendido = Column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    __table_args__ = (
        Index("ix_usuarios_email_lower", func.lower(email), unique=True),
    )

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


# Tabla de contadores de uso por plan
class UserUsageMonthly(Base):
    __tablename__ = "user_usage_monthly"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    period_yyyymm = Column(String, index=True, nullable=False)
    leads = Column(Integer, default=0)
    ia_msgs = Column(Integer, default=0)
    tasks = Column(Integer, default=0)
    csv_exports = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "period_yyyymm", name="uix_user_usage_monthly"),
    )


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
    dominio = Column(String, nullable=False)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    nicho = Column(String, nullable=False)  # Normalizado
    nicho_original = Column(String, nullable=False)
    estado_contacto = Column(String(20), nullable=False, server_default="pendiente", index=True)

    @validates("user_email")
    def _set_lower(self, key, value):
        self.user_email_lower = (value or "").strip().lower()
        return (value or "").strip()

    __table_args__ = (
        UniqueConstraint(
            "user_email_lower", "dominio", name="uix_leads_usuario_dominio"
        ),
    )


# Memoria de usuario almacenada en PostgreSQL
class UsuarioMemoria(Base):
    __tablename__ = "usuario_memoria"

    email_lower = Column(String, primary_key=True, index=True)
    descripcion = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HistorialExport(Base):
    """Historial de exportaciones de CSV por usuario."""

    __tablename__ = "historial"

    id = Column(Integer, primary_key=True)
    user_email = Column(String, nullable=False, index=True)
    filename = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    @validates("user_email")
    def _set_lower(self, key, value):
        return (value or "").strip().lower()


class LeadEstado(Base):
    """Estado de contacto de un lead por usuario."""

    __tablename__ = "lead_estado"

    id = Column(Integer, primary_key=True)
    user_email_lower = Column(String, nullable=False, index=True)
    url = Column(String)
    dominio = Column(String)
    estado = Column(String, nullable=False, server_default="pendiente")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_email_lower", "dominio", name="uix_lead_estado_usuario_dominio"
        ),
    )

    @validates("user_email_lower")
    def _lower(self, key, value):
        return (value or "").strip().lower()
