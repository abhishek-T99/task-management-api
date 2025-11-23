import pandas as pd
import numpy as np
import re
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging
from .models import CSVUpload, CSVData

logger = logging.getLogger(__name__)


def _to_snake_case(name: str) -> str:
    if name is None:
        name = ""
    s = str(name).strip()
    # camelCase boundary
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    # Non-alphanumeric to underscore
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s)
    s = s.lower()
    s = s.strip("_")
    if not s or re.match(r"^[0-9]", s):
        s = f"col_{s}" if s else "col"
    return s


@shared_task(bind=True)
def process_csv_file(self, upload_id):
    """
    Process large CSV file asynchronously with progress tracking
    """
    try:
        upload = CSVUpload.objects.get(id=upload_id)
        upload.status = "processing"
        upload.started_at = timezone.now()
        upload.save()

        # Update task_id for progress tracking
        upload.metadata["task_id"] = self.request.id
        upload.save()

        file_path = upload.file.path
        chunk_size = 50000

        # Get total rows for progress tracking
        total_rows = count_csv_rows(file_path)
        upload.total_rows = total_rows
        upload.save()

        logger.info(f"Starting to process {total_rows} rows from {file_path}")

        # Process CSV in chunks
        processed_rows = 0
        for chunk in pd.read_csv(file_path, chunksize=chunk_size, low_memory=False):
            # Normalize headers for each chunk and ensure uniqueness
            orig_cols = list(chunk.columns)
            new_cols = []
            seen = {}
            for col in orig_cols:
                base = _to_snake_case(col)
                candidate = base
                suffix = 1
                while candidate in seen:
                    candidate = f"{base}_{suffix}"
                    suffix += 1
                seen[candidate] = True
                new_cols.append(candidate)
            chunk.columns = new_cols

            processed_rows = process_chunk(upload, chunk, processed_rows)

            # Update progress
            upload.processed_rows = processed_rows
            upload.save()

            # Update cache for real-time progress (optional)
            progress = (processed_rows / total_rows) * 100 if total_rows else 0
            cache.set(f"upload_progress_{upload_id}", progress, 300)

            # Send progress update
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": processed_rows,
                    "total": total_rows,
                    "progress": progress,
                },
            )

        # Mark as completed
        upload.status = "completed"
        upload.completed_at = timezone.now()
        upload.save()

        logger.info(
            f"Successfully processed {processed_rows} rows for upload {upload_id}"
        )

        # Send completion email asynchronously
        try:
            send_upload_completed_email.delay(str(upload.id))
        except Exception:
            logger.exception("Failed to enqueue upload completed email task")

        return {
            "current": processed_rows,
            "total": total_rows,
            "status": "Completed successfully",
        }

    except Exception as e:
        logger.error(f"Error processing CSV upload {upload_id}: {str(e)}")

        # Update upload status to failed
        try:
            upload = CSVUpload.objects.get(id=upload_id)
            upload.status = "failed"
            upload.errors.append(str(e))
            upload.save()
        except Exception:
            logger.exception("Failed to mark upload as failed")

        raise self.retry(exc=e, countdown=10, max_retries=3)


def count_csv_rows(file_path):
    """Count total rows in CSV efficiently"""
    chunk_size = 10000
    total_rows = 0

    for chunk in pd.read_csv(file_path, chunksize=chunk_size, low_memory=False):
        total_rows += len(chunk)

    return total_rows


def process_chunk(upload, chunk, start_row):
    """Process a chunk of CSV data and bulk insert to database"""
    csv_data_objects = []

    # Clean and prepare data
    chunk = chunk.replace({np.nan: None})

    for index, row in chunk.iterrows():
        csv_data_objects.append(CSVData(upload=upload, data=row.to_dict()))

    # Bulk insert for performance
    if csv_data_objects:
        CSVData.objects.bulk_create(csv_data_objects, batch_size=1000)

    return start_row + len(chunk)


@shared_task(bind=True)
def send_upload_completed_email(self, upload_id):
    """Asynchronously render and send upload completion email with statistics."""
    try:
        upload = CSVUpload.objects.select_related("user").get(id=upload_id)
    except CSVUpload.DoesNotExist:
        logger.warning(f"CSVUpload {upload_id} not found for completion email")
        return

    # Prepare statistics
    total = upload.total_rows or 0
    processed = upload.processed_rows or 0
    started = upload.started_at
    completed = upload.completed_at
    duration = None
    if started and completed:
        duration = completed - started

    errors = upload.errors or []
    metadata = upload.metadata or {}

    # Sample columns and a sample row
    first_row = CSVData.objects.filter(upload=upload).first()
    columns = []
    sample_row = {}
    if first_row:
        sample_row = first_row.data
        columns = list(sample_row.keys())

    context = {
        "user": upload.user,
        "upload": upload,
        "total_rows": total,
        "processed_rows": processed,
        "duration": duration,
        "errors": errors,
        "metadata": metadata,
        "columns": columns,
        "sample_row": sample_row,
    }

    subject = f"CSV Upload Completed: {upload.original_filename}"

    plain = render_to_string("emails/csv_upload_completed.txt", context)
    html = render_to_string("emails/csv_upload_completed.html", context)

    to_email = [upload.user.email] if upload.user and upload.user.email else []
    if not to_email:
        logger.info(f"No recipient email for upload {upload_id}; skipping send")
        return

    msg = EmailMultiAlternatives(subject, plain, settings.DEFAULT_FROM_EMAIL, to_email)
    msg.attach_alternative(html, "text/html")
    try:
        msg.send(fail_silently=False)
        logger.info(f"Sent upload completed email for {upload_id} to {to_email}")
    except Exception:
        logger.exception(f"Failed to send upload completed email for {upload_id}")
