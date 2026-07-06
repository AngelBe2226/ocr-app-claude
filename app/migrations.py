"""Migraciones ligeras para SQLite.

create_all() crea tablas nuevas pero no añade columnas a tablas ya existentes.
Aquí añadimos con ALTER TABLE las columnas que falten en bases de datos previas."""
from sqlalchemy import text
from sqlalchemy.engine import Engine

# columnas nuevas por tabla: nombre -> definición SQL
NEW_COLUMNS = {
    "transactions": {
        "latitude": "FLOAT",
        "longitude": "FLOAT",
        "place_name": "VARCHAR DEFAULT ''",
    },
    "budgets": {
        "period": "VARCHAR DEFAULT 'monthly'",
    },
}


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        for table, columns in NEW_COLUMNS.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
