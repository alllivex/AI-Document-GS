from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel, Field


class SettingsInput(BaseModel):
    env_file: str = ".env"


class AppSettings(BaseModel):
    app_env: str = "dev"
    project_root: Path
    database_path: Path
    config_dir: Path
    templates_dir: Path
    tasks_dir: Path
    temp_dir: Path
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    @property
    def ai_available(self) -> bool:
        return bool(self.deepseek_api_key)


class _EnvFile(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "_EnvFile":
        if not path.exists():
            return cls()

        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
        return cls(values=values)

    def get(self, key: str, default: str | None = None) -> str | None:
        return os.getenv(key) or self.values.get(key) or default


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _database_path_from_url(project_root: Path, database_url: str) -> Path:
    sqlite_prefix = "sqlite:///"
    if database_url.startswith(sqlite_prefix):
        database_value = database_url[len(sqlite_prefix) :]
    else:
        database_value = database_url
    return _resolve_path(project_root, database_value)


def load_settings(settings_input: SettingsInput | None = None) -> AppSettings:
    input_value = settings_input or SettingsInput()
    env_file_path = Path(input_value.env_file)
    env_file = _EnvFile.load(env_file_path)

    default_project_root = Path(__file__).resolve().parents[3]
    project_root = Path(env_file.get("PROJECT_ROOT", str(default_project_root)) or default_project_root).resolve()
    database_url = env_file.get("DATABASE_URL", "sqlite:///config/db.sqlite") or "sqlite:///config/db.sqlite"

    return AppSettings(
        app_env=env_file.get("APP_ENV", "dev") or "dev",
        project_root=project_root,
        database_path=_database_path_from_url(project_root, database_url),
        config_dir=_resolve_path(project_root, env_file.get("CONFIG_DIR", "config") or "config"),
        templates_dir=_resolve_path(project_root, env_file.get("TEMPLATES_DIR", "templates") or "templates"),
        tasks_dir=_resolve_path(project_root, env_file.get("TASKS_DIR", "tasks") or "tasks"),
        temp_dir=_resolve_path(project_root, env_file.get("TEMP_DIR", "temp") or "temp"),
        deepseek_api_key=env_file.get("DEEPSEEK_API_KEY"),
        deepseek_base_url=env_file.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        or "https://api.deepseek.com/v1",
        deepseek_model=env_file.get("DEEPSEEK_MODEL", "deepseek-chat") or "deepseek-chat",
    )


@lru_cache
def get_settings() -> AppSettings:
    return load_settings()


def create_required_directories(settings: AppSettings | None = None) -> None:
    current_settings = settings or get_settings()
    for directory in (
        current_settings.config_dir,
        current_settings.templates_dir,
        current_settings.tasks_dir,
        current_settings.temp_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
