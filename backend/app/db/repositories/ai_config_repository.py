from __future__ import annotations

import sqlite3


class AIConfigRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.ensure_table()

    def ensure_table(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL DEFAULT 'deepseek',
                model_name TEXT NOT NULL DEFAULT 'deepseek-chat',
                base_url TEXT NOT NULL DEFAULT 'https://api.deepseek.com/v1',
                temperature REAL NOT NULL DEFAULT 0.2,
                timeout_seconds INTEGER NOT NULL DEFAULT 60,
                api_key_source TEXT NOT NULL DEFAULT 'env'
                    CHECK (api_key_source IN ('env', 'db', 'none')),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_model_configs_active ON ai_model_configs(is_active)"
        )

    def get_active(self) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT id, provider, model_name, base_url, temperature,
                   timeout_seconds, api_key_source, is_active, created_at, updated_at
            FROM ai_model_configs
            ORDER BY is_active DESC, updated_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()

    def upsert_active(
        self,
        provider: str,
        model_name: str,
        base_url: str,
        temperature: float,
        timeout_seconds: int,
        api_key_source: str,
        is_active: bool,
        now: str,
    ) -> None:
        self.connection.execute(
            "UPDATE ai_model_configs SET is_active = 0, updated_at = ? WHERE is_active = 1",
            (now,),
        )
        self.connection.execute(
            """
            INSERT INTO ai_model_configs (
                provider, model_name, base_url, temperature, timeout_seconds,
                api_key_source, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                model_name,
                base_url,
                temperature,
                timeout_seconds,
                api_key_source,
                int(is_active),
                now,
                now,
            ),
        )
