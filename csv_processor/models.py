# csvprocessor/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class CSVUpload(models.Model):
    UPLOAD_STATUS = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="csv_uploads/")
    total_rows = models.BigIntegerField(default=0)
    processed_rows = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=UPLOAD_STATUS, default="pending")
    errors = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "csv_uploads"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} - {self.status}"


class CSVData(models.Model):
    id = models.BigAutoField(primary_key=True)
    upload = models.ForeignKey(CSVUpload, on_delete=models.CASCADE, db_index=True)
    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "csv_data"
        indexes = [
            models.Index(fields=["upload"]),
        ]

    def __str__(self):
        return f"Upload {self.upload.id} - ID {self.id}"
