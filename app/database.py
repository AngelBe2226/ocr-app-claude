import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Base de datos:
#  - Por defecto: SQLite local (finance.db) — cero configuración, un solo dispositivo.
#  - Si defines la variable de entorno DATABASE_URL (p.ej. la de Neon/Postgres),
#    la app la usa automáticamente para compartir datos entre varios dispositivos.
#
# Neon entrega una URL tipo:
#   postgresql://usuario:clave@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
# SQLAlchemy necesita el driver psycopg (v3); normalizamos el prefijo a postgresql+psycopg://
DB_PATH = Path(__file__).resolve().parent.parent / "finance.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    IS_SQLITE = url.startswith("sqlite")
    # pool_pre_ping evita conexiones muertas con bases serverless (Neon) que se duermen.
    engine = create_engine(url, pool_pre_ping=True)
else:
    IS_SQLITE = True
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
