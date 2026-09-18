from django.contrib import admin

from apps.ml_models.models import DemandForecast, FraudFlag, TrustScoreLog


@admin.register(TrustScoreLog)
class TrustScoreLogAdmin(admin.ModelAdmin):
    list_display = ("worker", "score", "jobs_completed", "avg_rating", "computed_at")


@admin.register(DemandForecast)
class DemandForecastAdmin(admin.ModelAdmin):
    list_display = ("skill_category", "city", "period_start", "predicted_demand")
    list_filter = ("city", "skill_category")


@admin.register(FraudFlag)
class FraudFlagAdmin(admin.ModelAdmin):
    list_display = ("target_type", "target_id", "reason", "confidence", "resolved")
    list_filter = ("target_type", "resolved")
