from django.contrib import admin

from apps.employers.models import Employer


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("__str__", "employer_type", "city", "is_verified")
    list_filter = ("employer_type", "is_verified", "city")
    search_fields = ("user__username", "company_name", "city")
