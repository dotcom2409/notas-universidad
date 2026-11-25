"""Conexión a la base de datos.

Lee la configuración desde variables de entorno. Si DB_HOST no está definido,
usa SQLite local (solo para desarrollo rápido sin Docker).
"""
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "notas")
DB_USER = os.getenv("DB_USER", "notas_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

if DB_HOST:
    DATABASE_URL = (
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
else:
    DATABASE_URL = "sqlite:///./notas_dev.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(retries: int = 10, delay: int = 3) -> None:
    """Espera a que la BD acepte conexiones (útil cuando el contenedor arranca
    antes que PostgreSQL/RDS)."""
    for intento in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[db] intento {intento}/{retries} fallido: {exc.__class__.__name__}")
            time.sleep(delay)
    raise RuntimeError("No fue posible conectar a la base de datos")


def db_ok() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
