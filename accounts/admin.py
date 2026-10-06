from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, TelegramLink


@admin.register(User)
class EduUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("EduPlatform", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("EduPlatform", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_active", "is_staff")


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(TelegramLink, ReadOnlyAdmin)
admin.site.site_header = "EduPlatform · Администрирование"
