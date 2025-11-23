from rest_framework import serializers
from .models import CSVUpload


class CSVUploadCreateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = CSVUpload
        fields = ["file", "original_filename"]
        read_only_fields = ["original_filename"]

    def validate_file(self, value):
        # Validate file type
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("Only CSV files are allowed.")

        # Validate file size (400MB limit)
        max_size = 400 * 1024 * 1024  # 400MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError("File size must be less than 400MB.")

        return value

    def create(self, validated_data):
        # Set original filename from the uploaded file
        validated_data["original_filename"] = validated_data["file"].name
        return super().create(validated_data)


class CSVUploadSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()

    class Meta:
        model = CSVUpload
        fields = [
            "id",
            "original_filename",
            "total_rows",
            "processed_rows",
            "status",
            "progress",
            "duration",
            "created_at",
            "started_at",
            "completed_at",
            "errors",
            "file",
        ]
        read_only_fields = [
            "id",
            "original_filename",
            "total_rows",
            "processed_rows",
            "status",
            "created_at",
            "started_at",
            "completed_at",
            "errors",
            "file",
        ]

    def get_progress(self, obj):
        if obj.total_rows > 0:
            return round((obj.processed_rows / obj.total_rows) * 100, 2)
        return 0

    def get_duration(self, obj):
        if obj.completed_at and obj.started_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None
