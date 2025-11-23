from django.contrib import admin
from django.utils.html import format_html, escape
import json

from .models import CSVUpload, CSVData


@admin.register(CSVUpload)
class CSVUploadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "user",
        "status",
        "total_rows",
        "processed_rows",
        "created_at",
        "started_at",
        "completed_at",
    )
    list_filter = ("status", "user")
    search_fields = ("original_filename", "user__email", "id")
    readonly_fields = ("id", "created_at", "started_at", "completed_at")
    ordering = ("-created_at",)
    list_per_page = 25

    fieldsets = (
        (None, {"fields": ("id", "user", "original_filename", "file")}),
        (
            "Processing",
            {"fields": ("status", "total_rows", "processed_rows", "errors")},
        ),
        ("Timestamps", {"fields": ("created_at", "started_at", "completed_at")}),
        ("Metadata", {"fields": ("metadata",)}),
    )

    def errors_preview(self, obj):
        if not obj.errors:
            return "-"
        return format_html(
            "<pre style='max-width:600px; white-space:pre-wrap'>{}</pre>",
            escape(json.dumps(obj.errors)[:1000]),
        )


@admin.register(CSVData)
class CSVDataAdmin(admin.ModelAdmin):
    list_display = ("id", "upload", "short_data", "created_at")
    search_fields = ("upload__original_filename", "upload__id")
    list_filter = ("upload",)
    readonly_fields = ("id", "upload", "data", "created_at")
    ordering = ("id",)
    list_per_page = 100

    def short_data(self, obj):
        try:
            preview = json.dumps(obj.data, ensure_ascii=False)
        except Exception:
            preview = str(obj.data)
        # Truncate very long payloads for admin display
        if len(preview) > 500:
            preview = preview[:500] + "..."
        return format_html(
            "<pre style='max-width:800px; white-space:pre-wrap'>{}</pre>",
            escape(preview),
        )
