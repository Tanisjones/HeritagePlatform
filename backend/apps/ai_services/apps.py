import logging

from django.apps import AppConfig


class AiServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_services"

    def ready(self) -> None:
        from .ai_config import AIConfigError, load_ai_config

        logger = logging.getLogger(__name__)
        try:
            load_ai_config()
        except AIConfigError as exc:
            logger.warning("AI config not loaded: %s", exc)
