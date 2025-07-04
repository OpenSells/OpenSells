from sqlalchemy import Column, Integer, String, DateTime, func
from backend.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    plan = Column(String, default="free")
