"""
Configuración de base de datos - Módulo Bio-Adaptabilidad

Conexión a metrics.db (SQLite) y creación de tablas.
Ejecutar este módulo directamente para inicializar el esquema.

Uso:
    python -m src.bio.db

Autor: David Arroyo
Proyecto: Dialektos
"""

from pathlib import Path
from typing import Optional, Union

from sqlmodel import create_engine, SQLModel

from src.bio.models import DailyBiometrics


# Ruta por defecto: data/metrics.db (alineado con data/chroma_db del RAG)
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "metrics.db"


def get_engine(db_path: Optional[Union[Path, str]] = None):
    """Crea el motor SQLAlchemy para metrics.db."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{path}"
    return create_engine(url, echo=False)


def create_tables(engine=None):
    """Crea todas las tablas definidas en los modelos SQLModel."""
    if engine is None:
        engine = get_engine()
    SQLModel.metadata.create_all(engine)
    return engine


def init_metrics_db(db_path: Optional[Union[Path, str]] = None) -> None:
    """
    Inicializa la base de datos de métricas.

    Crea el directorio si no existe y todas las tablas del esquema.
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    engine = get_engine(path)
    create_tables(engine)
    print(f"✓ Base de datos inicializada: {path}")


if __name__ == "__main__":
    init_metrics_db()
