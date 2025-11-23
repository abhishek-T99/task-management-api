import time
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404
from django.db import connection
from django.db.models import Q
import json
import logging

from .models import CSVUpload, CSVData
from .serializers import CSVUploadSerializer, CSVUploadCreateSerializer
from .tasks import process_csv_file
from utils.cache import (
    get_cached_value,
    set_cached_value,
    invalidate_pattern,
)
from .pagination import CSVPagination, CSVStreamingPagination

logger = logging.getLogger(__name__)


@swagger_auto_schema(
    method="get",
    operation_summary="List CSV Uploads",
    operation_description="Get a list of all CSV uploads for the authenticated user",
    responses={200: CSVUploadSerializer(many=True)},
)
@swagger_auto_schema(
    method="post",
    operation_summary="Upload CSV File",
    operation_description="Uploads a CSV file and triggers async processing via Celery.",
    manual_parameters=[
        openapi.Parameter(
            "file",
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            description="CSV file to upload (max 400MB)",
            required=True,
        ),
    ],
    request_body=CSVUploadCreateSerializer,
    responses={201: CSVUploadSerializer, 400: "Bad request"},
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def csv_upload_list_create(request):
    """
    List all CSV uploads or create a new upload
    """
    if request.method == "GET":
        uploads = CSVUpload.objects.filter(user=request.user)
        serializer = CSVUploadSerializer(uploads, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        # Use the create serializer for POST
        serializer = CSVUploadCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Save the upload with the file
                    upload = serializer.save(user=request.user)

                    # Verify the file was saved and has a path
                    if not upload.file:
                        raise ValueError("File was not saved properly")

                    # Start async processing
                    process_csv_file.delay(str(upload.id))

                    # Return full upload details using the main serializer
                    response_serializer = CSVUploadSerializer(upload)
                    return Response(
                        response_serializer.data, status=status.HTTP_201_CREATED
                    )

            except Exception as e:
                # If something fails during save, return error
                return Response(
                    {"error": f"Failed to save upload: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def csv_upload_detail(request, upload_id):
    upload = get_object_or_404(CSVUpload, id=upload_id, user=request.user)
    serializer = CSVUploadSerializer(upload)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def csv_upload_progress(request, upload_id):
    upload = get_object_or_404(CSVUpload, id=upload_id, user=request.user)

    progress_data = {
        "status": upload.status,
        "processed_rows": upload.processed_rows,
        "total_rows": upload.total_rows,
        "progress": f"{round((upload.processed_rows / upload.total_rows) * 100, 2) if upload.total_rows > 0 else 0}%",
    }

    return Response(progress_data)


@swagger_auto_schema(
    method="get",
    operation_summary="Get CSV Data",
    operation_description="Get paginated CSV data with filtering, sorting, searching, column selection, and caching",
    manual_parameters=[
        openapi.Parameter(
            "page",
            openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Page number (default: 1)",
            default=1,
        ),
        openapi.Parameter(
            "page_size",
            openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Page size (max: 500, default: 100)",
            default=100,
        ),
        openapi.Parameter(
            "sort_by",
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Sort by field: 'id' (default) or any CSV column name",
        ),
        openapi.Parameter(
            "sort_order",
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Sort order: 'asc' or 'desc' (default: 'asc')",
            default="asc",
        ),
        openapi.Parameter(
            "search",
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Search text across all columns",
        ),
        openapi.Parameter(
            "columns",
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Comma-separated list of columns to return",
        ),
        openapi.Parameter(
            "filters",
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="JSON string for column filters: {'column1': 'value1', 'column2': 'value2'}",
        ),
        openapi.Parameter(
            "nocache",
            openapi.IN_QUERY,
            type=openapi.TYPE_BOOLEAN,
            description="Bypass cache",
            default=False,
        ),
    ],
    responses={
        200: openapi.Response(
            "Success",
            examples={
                "application/json": {
                    "upload_id": "uuid",
                    "original_filename": "file.csv",
                    "upload_status": "completed",
                    "data": [
                        {
                            "row_id": 1,
                            "data": {"col1": "value1", "col2": "value2"},
                            "created_at": "2023-01-01T00:00:00Z",
                        }
                    ],
                    "pagination": {
                        "page": 1,
                        "page_size": 100,
                        "total_count": 1000,
                        "total_pages": 10,
                        "has_next": True,
                        "has_prev": False,
                    },
                    "metadata": {
                        "available_columns": ["col1", "col2", "col3"],
                        "search_query": None,
                        "sort_by": "id",
                        "sort_order": "asc",
                        "columns_filter": ["col1", "col2"],
                        "applied_filters": {"col1": "value1"},
                    },
                    "performance": {
                        "response_time_ms": 45.2,
                        "cached": False,
                        "query_count": 2,
                    },
                }
            },
        )
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def csv_upload_data(request, upload_id):
    """
    Get paginated CSV data with advanced optimizations, caching, and filtering
    """
    start_time = time.time()
    initial_queries = len(connection.queries)

    # Get upload and validate access
    upload = get_object_or_404(CSVUpload, id=upload_id, user=request.user)

    # Validate that upload is completed
    if upload.status != "completed":
        return Response(
            {
                "error": f"CSV upload is still {upload.status}. Please wait for processing to complete."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse and validate parameters
    try:
        page = max(1, int(request.GET.get("page", 1)))
        page_size = min(max(1, int(request.GET.get("page_size", 100))), 500)
        sort_by = request.GET.get("sort_by", "id")
        sort_order = request.GET.get("sort_order", "asc")
        search_query = request.GET.get("search", "").strip()
        columns_filter = request.GET.get("columns", "").strip()
        filters_json = request.GET.get("filters", "").strip()
        nocache = request.GET.get("nocache", "false").lower() == "true"
    except (ValueError, TypeError) as e:
        return Response(
            {"error": f"Invalid parameters: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse filters
    filters = {}
    if filters_json:
        try:
            filters = json.loads(filters_json)
            if not isinstance(filters, dict):
                raise ValueError("Filters must be a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            return Response(
                {"error": f"Invalid filters format: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Generate cache key
    cache_key = f"csv_data:{upload_id}:{page}:{page_size}:{sort_by}:{sort_order}:{search_query}:{columns_filter}:{json.dumps(filters, sort_keys=True)}"

    # Try to get from cache first (unless nocache is True)
    if not nocache:
        cached_data = get_cached_value(cache_key)
        if cached_data:
            cached_data["performance"]["cached"] = True
            cached_data["performance"]["response_time_ms"] = round(
                (time.time() - start_time) * 1000, 2
            )
            return Response(cached_data)

    # Get available columns from the first row (cached)
    columns_cache_key = f"csv_columns:{upload_id}"
    available_columns = get_cached_value(columns_cache_key)

    if available_columns is None:
        first_row = CSVData.objects.filter(upload=upload).first()
        if first_row and first_row.data:
            available_columns = list(first_row.data.keys())
            set_cached_value(columns_cache_key, available_columns, timeout=3600)
        else:
            available_columns = []

    # Parse columns to include
    columns_to_include = []
    if columns_filter:
        requested_columns = [col.strip() for col in columns_filter.split(",")]
        columns_to_include = [
            col for col in requested_columns if col in available_columns
        ]

    # Build optimized query
    data_queryset = CSVData.objects.filter(upload=upload).select_related("upload")

    # Apply search if provided
    if search_query:
        # Create OR conditions for all available columns
        search_conditions = Q()
        for column in available_columns:
            search_conditions |= Q(**{f"data__{column}__icontains": search_query})
        data_queryset = data_queryset.filter(search_conditions)

    # Apply column filters
    for column, value in filters.items():
        if column in available_columns and value:
            if isinstance(value, list):
                # Handle multiple values (OR condition)
                filter_condition = Q()
                for val in value:
                    filter_condition |= Q(**{f"data__{column}__icontains": str(val)})
                data_queryset = data_queryset.filter(filter_condition)
            else:
                data_queryset = data_queryset.filter(
                    **{f"data__{column}__icontains": str(value)}
                )

    # Apply sorting (use the primary key 'id' for stable DB ordering)
    if sort_by == "id":
        if sort_order == "desc":
            data_queryset = data_queryset.order_by("-id")
        else:
            data_queryset = data_queryset.order_by("id")
    else:
        # Keep DB ordering by id; JSON-field sorting will be done in memory later if requested
        data_queryset = data_queryset.order_by("id")

    # Use the custom paginator (supports caching/count optimizations)
    # Allow streaming by passing ?pagination=streaming
    pagination_type = request.GET.get("pagination", "").lower()
    if pagination_type == "streaming":
        paginator = CSVStreamingPagination()
    else:
        paginator = CSVPagination()

    page_objs = paginator.paginate_queryset(data_queryset, request)

    # Process data
    processed_data = []
    for csv_data in page_objs:
        row_data = csv_data.data

        # Filter columns if specified
        if columns_to_include:
            row_data = {col: row_data.get(col) for col in columns_to_include}

        processed_data.append(
            {
                "row_id": csv_data.id,
                "data": row_data,
                "created_at": (
                    csv_data.created_at.isoformat() if csv_data.created_at else None
                ),
            }
        )

    # Apply in-memory sorting for JSON fields if needed
    if sort_by in available_columns and sort_by != "id":
        try:
            reverse = sort_order == "desc"
            processed_data.sort(
                key=lambda x: str(x["data"].get(sort_by, "")).lower(),
                reverse=reverse,
            )
        except Exception:
            processed_data.sort(key=lambda x: x["row_id"])

    # Build response using paginator's metadata and merge additional info
    paginator_response = paginator.get_paginated_response(processed_data)
    # paginator_response.data contains {'data','pagination','performance'}
    response_data = paginator_response.data or {}
    # Ensure expected keys exist to avoid runtime/key errors
    response_data.setdefault("data", processed_data)
    response_data.setdefault("pagination", {})
    response_data.setdefault("performance", {})

    # Merge our upload-level metadata
    response_data.update(
        {
            "upload_id": str(upload.id),
            "original_filename": upload.original_filename,
            "upload_status": upload.status,
            "metadata": {
                "available_columns": available_columns,
                "search_query": search_query if search_query else None,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "columns_filter": columns_to_include if columns_to_include else "all",
                "applied_filters": filters if filters else None,
            },
        }
    )

    # Augment performance metadata
    response_data["performance"].update(
        {
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "query_count": len(connection.queries) - initial_queries,
            "total_rows_processed": upload.processed_rows,
            "cached": response_data["performance"].get("cached", False),
        }
    )

    # Cache the response for 5 minutes using the existing cache key
    if not nocache:
        set_cached_value(cache_key, response_data, timeout=300)

    return Response(response_data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def csv_upload_delete(request, upload_id):
    upload = get_object_or_404(CSVUpload, id=upload_id, user=request.user)

    # Delete associated file from storage
    if upload.file:
        upload.file.delete(save=False)

    # Delete the upload record (this will cascade delete CSVData records due to ForeignKey)
    upload.delete()

    # Invalidate related cache (best-effort)
    try:
        invalidate_pattern(f"csv_data:{upload_id}")
        invalidate_pattern(f"csv_columns:{upload_id}")
        invalidate_pattern(f"csv_data_count:{upload_id}")
    except Exception:
        pass

    return Response(
        {"message": "CSV upload and associated data deleted successfully"},
        status=status.HTTP_204_NO_CONTENT,
    )
