from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.db.connection import connect

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def init_db(database_path: Path | None = None, schema_path: Path | None = None) -> Path:
    target_path = database_path or get_settings().database_path
    schema_sql = (schema_path or SCHEMA_PATH).read_text(encoding="utf-8")

    with connect(target_path) as connection:
        connection.executescript(schema_sql)

    return target_path


if __name__ == "__main__":
    print(init_db())
