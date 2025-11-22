from django.contrib import admin
from .models import Task


class TaskAdmin(admin.ModelAdmin):
    search_fields = ["title", "status", "priority"]
    list_display = ["title", "status", "priority", "user", "due_date"]
    readonly_fields = ["user"]


admin.site.register(Task, TaskAdmin)
