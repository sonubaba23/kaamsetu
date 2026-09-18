from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.models import SkillCategory, User


@admin.register(User)
class KaamSetuUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "phone_number", "is_phone_verified", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("KaamSetu", {"fields": ("role", "phone_number", "is_phone_verified")}),
    )


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
