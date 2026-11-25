"""Modelo de datos: estudiantes, asignaturas y notas por corte."""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

# Porcentaje de cada corte en la nota definitiva (escala colombiana 0.0 - 5.0)
PESOS_CORTE = {1: 0.30, 2: 0.30, 3: 0.40}
NOTA_APROBATORIA = 3.0


class Estudiante(Base):
    __tablename__ = "estudiantes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    programa: Mapped[str] = mapped_column(String(120), nullable=False)
    creado: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    notas: Mapped[list["Nota"]] = relationship(
        back_populates="estudiante", cascade="all, delete-orphan"
    )


class Asignatura(Base):
    __tablename__ = "asignaturas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    creditos: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    notas: Mapped[list["Nota"]] = relationship(
        back_populates="asignatura", cascade="all, delete-orphan"
    )

    __table_args__ = (CheckConstraint("creditos BETWEEN 1 AND 10", name="ck_creditos"),)


class Nota(Base):
    __tablename__ = "notas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estudiante_id: Mapped[int] = mapped_column(
        ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False
    )
    asignatura_id: Mapped[int] = mapped_column(
        ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False
    )
    corte: Mapped[int] = mapped_column(Integer, nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    registrada: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    estudiante: Mapped[Estudiante] = relationship(back_populates="notas")
    asignatura: Mapped[Asignatura] = relationship(back_populates="notas")

    __table_args__ = (
        CheckConstraint("valor >= 0 AND valor <= 5", name="ck_valor_rango"),
        CheckConstraint("corte IN (1, 2, 3)", name="ck_corte"),
        UniqueConstraint("estudiante_id", "asignatura_id", "corte", name="uq_nota_corte"),
    )


def definitiva(notas: list[Nota]) -> float | None:
    """Calcula la nota definitiva ponderada. Devuelve None si faltan cortes."""
    por_corte = {n.corte: float(n.valor) for n in notas}
    if set(por_corte) != set(PESOS_CORTE):
        return None
    return round(sum(por_corte[c] * p for c, p in PESOS_CORTE.items()), 2)
