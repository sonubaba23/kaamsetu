import logging

from celery import shared_task

from apps.ml_models.demand_forecasting import update_all_forecasts

logger = logging.getLogger(__name__)


@shared_task(name="apps.ml_models.tasks.update_all_forecasts_task")
def update_all_forecasts_task():
    """Regenerate demand forecasts for every skill/city pair with job history."""
    forecasts = update_all_forecasts()
    logger.info("Generated %d demand forecast(s).", len(forecasts))
    return len(forecasts)
