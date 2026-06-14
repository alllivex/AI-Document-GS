from __future__ import annotations

import sqlite3

from app.core.config import AppSettings, get_settings
from app.engine.generation_runner import GenerateTaskInput, GenerateTaskResult, generate_task


class GenerationService:
    def __init__(self, connection: sqlite3.Connection, settings: AppSettings | None = None) -> None:
        self.connection = connection
        self.settings = settings or get_settings()

    def generate_task(
        self,
        task_id: str,
        force: bool = False,
        ai_enabled: bool = True,
    ) -> GenerateTaskResult:
        return generate_task(
            GenerateTaskInput(task_id=task_id, force=force, ai_enabled=ai_enabled),
            connection=self.connection,
            settings=self.settings,
        )
