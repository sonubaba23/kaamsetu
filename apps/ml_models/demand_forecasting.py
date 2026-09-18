"""Demand forecasting for a skill category in a city.

Historical job-posting counts, grouped by week, stand in for labor
demand. With enough history, Prophet (additive trend + seasonality) fits
that time series and projects it forward with confidence bounds. A new
marketplace won't have months of weekly data on day one, so below
MIN_HISTORY_WEEKS this falls back to a naive flat forecast off the
recent average, with deliberately wide bounds to reflect the low
confidence — better than crashing or fabricating false precision.

Each run appends new DemandForecast rows (like TrustScoreLog); it never
edits a previous forecast in place, so trend charts can show how
predictions evolved as more data came in.
"""

from datetime import timedelta
from typing import Optional

import pandas as pd
from django.db.models import Count
from django.db.models.functions import TruncWeek
from django.utils import timezone

from apps.core.models import SkillCategory
from apps.jobs.models import Job
from apps.ml_models.models import DemandForecast

MODEL_VERSION = "v1"
FORECAST_PERIODS = 4  # Weeks ahead to forecast.
MIN_HISTORY_WEEKS = 8  # Below this, Prophet's fit is unreliable; use the naive fallback.
NAIVE_LOOKBACK_WEEKS = 4


def _weekly_job_counts(skill_category: SkillCategory, city: str) -> pd.DataFrame:
    rows = (
        Job.objects.filter(skill_category=skill_category, city=city)
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(count=Count("id"))
        .order_by("week")
    )
    df = pd.DataFrame(list(rows))
    if df.empty:
        return pd.DataFrame(columns=["ds", "y"])
    return df.rename(columns={"week": "ds", "count": "y"})


def _target_week_starts(periods: int) -> list:
    """The next `periods` Mondays, starting with next week (so 'now' is never mid-period)."""
    today = timezone.localdate()
    days_until_next_monday = (7 - today.weekday()) % 7 or 7
    first_start = today + timedelta(days=days_until_next_monday)
    return [first_start + timedelta(weeks=i) for i in range(periods)]


def _naive_forecast(history: pd.DataFrame, target_starts: list) -> list[dict]:
    recent_avg = float(history["y"].tail(NAIVE_LOOKBACK_WEEKS).mean()) if not history.empty else 0.0
    predicted = max(0, round(recent_avg))
    # Wide, asymmetric-looking-but-simple bounds: reflects that this is a low-confidence guess.
    lower = max(0, round(recent_avg * 0.4))
    upper = max(predicted, round(recent_avg * 1.8) or 2)
    return [
        {"predicted_demand": predicted, "confidence_lower": lower, "confidence_upper": upper}
        for _ in target_starts
    ]


def _prophet_forecast(history: pd.DataFrame, target_starts: list) -> list[dict]:
    from prophet import Prophet

    df = history.copy()
    df["ds"] = pd.to_datetime(df["ds"])
    if df["ds"].dt.tz is not None:
        df["ds"] = df["ds"].dt.tz_convert(None)  # Prophet requires timezone-naive timestamps.

    model = Prophet(
        weekly_seasonality=False,
        yearly_seasonality=len(df) >= 52,
        interval_width=0.8,
    )
    model.fit(df)

    future = pd.DataFrame({"ds": pd.to_datetime(target_starts)})
    forecast = model.predict(future)

    return [
        {
            "predicted_demand": max(0, round(row.yhat)),
            "confidence_lower": max(0, round(row.yhat_lower)),
            "confidence_upper": max(0, round(row.yhat_upper)),
        }
        for row in forecast.itertuples()
    ]


def forecast_demand(skill_category: SkillCategory, city: str, periods: int = FORECAST_PERIODS) -> list[dict]:
    """Compute upcoming weekly demand predictions, without saving anything."""
    history = _weekly_job_counts(skill_category, city)
    target_starts = _target_week_starts(periods)

    if len(history) < MIN_HISTORY_WEEKS:
        predictions = _naive_forecast(history, target_starts)
        model_version = f"{MODEL_VERSION}-naive"
    else:
        predictions = _prophet_forecast(history, target_starts)
        model_version = f"{MODEL_VERSION}-prophet"

    return [
        {
            "period_start": start,
            "period_end": start + timedelta(days=6),
            "predicted_demand": pred["predicted_demand"],
            "confidence_lower": pred["confidence_lower"],
            "confidence_upper": pred["confidence_upper"],
            "model_version": model_version,
        }
        for start, pred in zip(target_starts, predictions)
    ]


def update_forecast(
    skill_category: SkillCategory, city: str, periods: int = FORECAST_PERIODS
) -> list[DemandForecast]:
    """Compute and persist a fresh batch of forecasts for one skill/city pair."""
    predictions = forecast_demand(skill_category, city, periods)
    return DemandForecast.objects.bulk_create(
        DemandForecast(skill_category=skill_category, city=city, **p) for p in predictions
    )


def update_all_forecasts(periods: int = FORECAST_PERIODS) -> list[DemandForecast]:
    """Run update_forecast for every skill/city combination with at least one job posted."""
    combos = (
        Job.objects.values_list("skill_category_id", "city").distinct().order_by("skill_category_id", "city")
    )

    all_forecasts: list[DemandForecast] = []
    skill_categories = {c.id: c for c in SkillCategory.objects.all()}
    for skill_category_id, city in combos:
        skill_category = skill_categories.get(skill_category_id)
        if skill_category is None:
            continue
        all_forecasts.extend(update_forecast(skill_category, city, periods))
    return all_forecasts
