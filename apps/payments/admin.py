from django.contrib import admin

from apps.payments.models import Escrow


@admin.register(Escrow)
class EscrowAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "booking", "amount", "status", "held_at", "released_at")
    list_filter = ("status",)
