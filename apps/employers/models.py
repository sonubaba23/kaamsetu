from django.conf import settings
from django.db import models


class Employer(models.Model):
    class EmployerType(models.TextChoices):
        HOUSEHOLD = "household", "Household"
        CONTRACTOR = "contractor", "Contractor"
        COMPANY = "company", "Company"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employer_profile"
    )
    employer_type = models.CharField(
        max_length=10, choices=EmployerType.choices, default=EmployerType.HOUSEHOLD
    )
    company_name = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name or self.user.get_full_name() or self.user.username

    @property
    def total_spend(self):
        from apps.payments.models import Escrow

        agg = Escrow.objects.filter(
            booking__job__employer=self, status=Escrow.Status.RELEASED
        ).aggregate(models.Sum("amount"))
        return agg["amount__sum"] or 0
