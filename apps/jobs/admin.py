from django.contrib import admin

from apps.jobs.models import Booking, Job, Review


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "skill_category", "city", "status", "created_at")
    list_filter = ("status", "skill_category", "city")
    search_fields = ("title", "city")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("worker", "job", "status", "agreed_wage", "created_at")
    list_filter = ("status",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("worker", "employer", "rating", "is_flagged_fake", "created_at")
    list_filter = ("rating", "is_flagged_fake")
