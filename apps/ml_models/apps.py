from django.apps import AppConfig


class MlModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ml_models'
    label = 'ml_models'

    def ready(self):
        from apps.ml_models import signals  # noqa: F401
