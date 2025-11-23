from django.contrib import admin
from .models import User


class UserAdmin(admin.ModelAdmin):
    search_fields = ["full_name", "username", "email"]
    list_display = ["username", "email", "full_name", "is_active"]
    exclude = ["password"]


admin.site.register(User, UserAdmin)
