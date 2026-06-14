from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.init_db import init_db


def test_init_db_creates_contract_tables(tmp_path) -> None:
    database_path = tmp_path / "config" / "db.sqlite"

    init_db(database_path)

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert {
        "templates",
        "template_tables",
        "fields",
        "tasks",
        "uploaded_files",
        "documents",
        "generation_logs",
        "validation_reports",
    }.issubset(table_names)
