import logging

from app.core.config import AppSettings


def configure_logging(settings: AppSettings) -> None:
    level = logging.DEBUG if settings.app_env == "dev" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
