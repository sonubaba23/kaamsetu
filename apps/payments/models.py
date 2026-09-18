import uuid

from django.db import models

from apps.jobs.models import Booking


class Escrow(models.Model):
    class Status(models.TextChoices):
        HELD = "held", "Held in escrow"
        RELEASED = "released", "Released to worker"
        REFUNDED = "refunded", "Refunded to employer"
        DISPUTED = "disputed", "Disputed"

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="escrow")
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.HELD)

    held_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-held_at"]

    def __str__(self):
        return f"Escrow {self.transaction_id} - {self.status}"
