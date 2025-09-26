from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Date,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    func,
    text,
    UniqueConstraint,
    Index,
    event,
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
    user_email_lower = Column(String, nullable=False, index=True)  # <- NUEVA COLUMNA
    hashed_password = Column(String, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    plan = Column(String, default="free", server_default="free", nullable=False)
    suspendido = Column(Boolean, default=False, server_default=text("false"), nullable=False)

    __table_args__ = (
        Index("ix_usuarios_email_lower", func.lower(email), unique=True),
    )

    @validates("email")
    def _set_lower(self, key, value):
        v = (value or "").strip()
        self.user_email_lower = v.lower()
        return v

# Tabla de tareas
class LeadTarea(Base):
    __tablename__ = "lead_tarea"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    user_email_lower = Column(String, index=True, nullable=False)
    dominio = Column(String, nullable=True)
    texto = Column(Text, nullable=False)
    fecha = Column(Date, nullable=True)
    completado = Column(Boolean, default=False, server_default=text("false"), nullable=False)
    # Triple defensa contra NULL: default Python, server_default en BD y nullable=False
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    tipo = Column(String, nullable=False)
    nicho = Column(String, nullable=True)
    prioridad = Column(String, nullable=False, server_default=text("'media'"))
    auto = Column(Boolean, nullable=False, server_default=text("false"))

    @validates("email")
    def _set_lower(self, key, value):
        self.user_email_lower = (value or "").strip().lower()
        return (value or "").strip()


@event.listens_for(LeadTarea, "before_insert", propagate=True)
def _lead_tarea_defaults(mapper, connection, target):
    """Última línea de defensa para columnas críticas sin valores."""
    if not getattr(target, "user_email_lower", None) and getattr(target, "email", None):
        try:
            target.user_email_lower = target.email.lower()
        except Exception:
            pass

    if not getattr(target, "prioridad", None):
        target.prioridad = "media"

    if getattr(target, "completado", None) is None:
        target.completado = False

    if getattr(target, "timestamp", None) is None:
        try:
            target.timestamp = datetime.now(timezone.utc)
        except Exception:
            target.timestamp = datetime.utcnow()

# Tabla de historial
class LeadHistorial(Base):
    __tablename__ = "lead_historial"
    __table_args__ = (
        Index(
            "idx_lead_historial_user_tipo_nicho",
            "user_email_lower",
            "tipo",
            "nicho",
        ),
        Index(
            "idx_lead_historial_user_tipo_dominio",
            "user_email_lower",
            "tipo",
            "dominio",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    email = Column(Text, nullable=True)
    user_email_lower = Column(Text, index=True, nullable=False)
    dominio = Column(Text, nullable=True)
    nicho = Column(Text, nullable=True)
    tipo = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @validates("email")
    def _set_lower(self, key, value):
        cleaned = (value or "").strip()
        if cleaned:
            self.user_email_lower = cleaned.lower()
        return cleaned


# Tabla de contadores de uso por plan
class UserUsageMonthly(Base):
    __tablename__ = "user_usage_monthly"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_yyyymm = Column(String(6), nullable=False)
    leads = Column(Integer, nullable=False, default=0, server_default=text("0"))
    ia_msgs = Column(Integer, nullable=False, default=0, server_default=text("0"))
    tasks = Column(Integer, nullable=False, default=0, server_default=text("0"))
    csv_exports = Column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "period_yyyymm", name="user_usage_monthly_user_period_uk"),
        Index("idx_user_usage_monthly_user", "user_id"),
        Index("idx_user_usage_monthly_period", "period_yyyymm"),
    )


class UserUsageDaily(Base):
    __tablename__ = "user_usage_daily"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_yyyymmdd = Column(String(8), nullable=False)
    ia_msgs = Column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "period_yyyymmdd", name="user_usage_daily_user_period_uk"),
        Index("idx_user_usage_daily_user", "user_id"),
        Index("idx_user_usage_daily_period", "period_yyyymmdd"),
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
    user_email_lower = Column(String, nullable=False, index=True)
    dominio = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    informacion = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_email_lower",
            "dominio",
            name="uix_lead_info_extra_usuario_dominio",
        ),
    )

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

    # Clave lógica única por email normalizado (úsala como PK)
    email_lower = Column(String, primary_key=True, nullable=False, unique=True)

    # Representa el email normalizado del usuario (mismo valor que email_lower)
    user_email_lower = Column(String, nullable=False, index=True)

    descripcion = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("email_lower", name="usuario_memoria_email_lower_key"),
    )

    def __repr__(self):
        return f"<UsuarioMemoria email_lower={self.email_lower!r}>"


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
    dominio = Column(String, nullable=False, index=True)
    estado = Column(
        String,
        nullable=False,
        server_default="pendiente",
        default="pendiente",
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_email_lower", "dominio", name="uix_lead_estado_usuario_dominio"
        ),
    )

    @validates("user_email_lower")
    def _lower(self, key, value):
        return (value or "").strip().lower()
