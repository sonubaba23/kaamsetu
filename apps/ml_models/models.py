from django.db import models

from apps.core.models import SkillCategory
from apps.workers.models import Worker


class TrustScoreLog(models.Model):
    """Snapshot of a trust-score computation, for audit and trend charts."""

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name="trust_score_logs")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    jobs_completed = models.PositiveIntegerField(default=0)
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    punctuality_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    model_version = models.CharField(max_length=30, default="v1")
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-computed_at"]


class DemandForecast(models.Model):
    """Predicted demand for a skill in a city/area over an upcoming period."""

    skill_category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name="forecasts")
    city = models.CharField(max_length=100)
    period_start = models.DateField()
    period_end = models.DateField()
    predicted_demand = models.PositiveIntegerField(help_text="Predicted number of job postings")
    confidence_lower = models.PositiveIntegerField(null=True, blank=True)
    confidence_upper = models.PositiveIntegerField(null=True, blank=True)
    model_version = models.CharField(max_length=30, default="v1")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [models.Index(fields=["city", "skill_category"])]


class FraudFlag(models.Model):
    class TargetType(models.TextChoices):
        REVIEW = "review", "Review"
        WORKER_PROFILE = "worker_profile", "Worker profile"

    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=200)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
