from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SkillCategory


class Worker(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_profile"
    )
    skill_category = models.ForeignKey(
        SkillCategory, on_delete=models.PROTECT, related_name="workers"
    )
    bio = models.TextField(blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0)
    daily_wage = models.DecimalField(max_digits=8, decimal_places=2)

    # Service area
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    service_radius_km = models.PositiveSmallIntegerField(default=10)

    # Verification
    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    id_proof = models.FileField(upload_to="worker_docs/id_proof/", null=True, blank=True)
    is_live = models.BooleanField(default=False, help_text="Profile is publicly visible")

    # ML-derived fields (updated by trust score / fraud modules)
    trust_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-trust_score", "-created_at"]
        indexes = [
            models.Index(fields=["city", "skill_category"]),
            models.Index(fields=["-trust_score"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.skill_category})"

    @property
    def jobs_completed(self):
        return self.bookings.filter(status="completed").count()

    @property
    def average_rating(self):
        agg = self.reviews.aggregate(models.Avg("rating"))
        return round(agg["rating__avg"] or 0, 2)


class PortfolioImage(models.Model):
    class QualityGrade(models.TextChoices):
        UNGRADED = "ungraded", "Ungraded"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name="portfolio")
    image = models.ImageField(upload_to="worker_portfolio/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)

    # CNN skill-verification output
    predicted_trade = models.ForeignKey(
        SkillCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    prediction_confidence = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    quality_grade = models.CharField(
        max_length=10, choices=QualityGrade.choices, default=QualityGrade.UNGRADED
    )
    is_flagged = models.BooleanField(default=False, help_text="Flagged as mismatched/suspicious")

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Portfolio image #{self.pk} - {self.worker}"
