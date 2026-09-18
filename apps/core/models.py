from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        WORKER = "worker", "Worker"
        EMPLOYER = "employer", "Employer"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.WORKER)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class SkillCategory(models.Model):
    """Trade categories: mason, plumber, electrician, painter, carpenter, welder, ..."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon identifier for the UI")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Skill categories"
        ordering = ["name"]

    def __str__(self):
        return self.name
