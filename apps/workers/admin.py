from django.contrib import admin

from apps.workers.models import PortfolioImage, Worker


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 0


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ("user", "skill_category", "city", "trust_score", "verification_status", "is_live")
    list_filter = ("verification_status", "skill_category", "city", "is_live")
    search_fields = ("user__username", "user__first_name", "user__last_name", "city")
    inlines = [PortfolioImageInline]


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ("worker", "predicted_trade", "quality_grade", "is_flagged", "uploaded_at")
    list_filter = ("quality_grade", "is_flagged")
