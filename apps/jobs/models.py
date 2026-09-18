from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SkillCategory
from apps.employers.models import Employer
from apps.workers.models import Worker


class Job(models.Model):
    class WageType(models.TextChoices):
        DAILY = "daily", "Daily wage"
        FIXED = "fixed", "Fixed price"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="jobs")
    skill_category = models.ForeignKey(
        SkillCategory, on_delete=models.PROTECT, related_name="jobs"
    )
    title = models.CharField(max_length=150)
    description = models.TextField()

    city = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    wage_type = models.CharField(max_length=10, choices=WageType.choices, default=WageType.DAILY)
    budget_min = models.DecimalField(max_digits=9, decimal_places=2)
    budget_max = models.DecimalField(max_digits=9, decimal_places=2)
    workers_required = models.PositiveSmallIntegerField(default=1)

    start_date = models.DateField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city", "skill_category", "status"]),
        ]

    def __str__(self):
        return self.title


class Booking(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="bookings")
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name="bookings")
    agreed_wage = models.DecimalField(max_digits=9, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.REQUESTED)

    scheduled_start = models.DateField(null=True, blank=True)
    scheduled_end = models.DateField(null=True, blank=True)

    is_punctual = models.BooleanField(null=True, blank=True, help_text="Set on completion")
    cancelled_by = models.CharField(
        max_length=10, choices=[("worker", "Worker"), ("employer", "Employer")], blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "worker"], name="unique_worker_booking_per_job"
            )
        ]

    def __str__(self):
        return f"{self.worker} -> {self.job} ({self.status})"


class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name="reviews")
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="reviews_given")

    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    # Fraud/NLP module outputs
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    is_flagged_fake = models.BooleanField(default=False)
    fraud_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review for {self.worker} - {self.rating}★"
