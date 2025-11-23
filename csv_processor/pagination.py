from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from django.core.paginator import Paginator, EmptyPage
from utils.cache import get_cached_value, set_cached_value
import math
from typing import Dict, Any, List


class CSVPagination(BasePagination):
    """
    Optimized pagination for large CSV datasets with caching and performance features
    """

    page_size = 100
    max_page_size = 500
    page_size_query_param = "page_size"
    page_query_param = "page"

    # Cache settings
    count_cache_timeout = 600  # 10 minutes
    page_cache_timeout = 300  # 5 minutes

    def __init__(self):
        self.request = None
        self.queryset = None
        self.page_number: int = -1
        self.page_size: int = -1
        self.total_count: int = 0
        self.paginator = None
        self.page = None

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate the queryset with optimizations for large datasets
        """
        self.request = request
        self.queryset = queryset

        # Get pagination parameters
        self.page_number = self._get_page_number(request)
        self.page_size = self._get_page_size(request)

        # Get total count with caching
        self.total_count = self._get_cached_count(queryset, request)

        # Create paginator (but don't evaluate the full queryset)
        self.paginator = Paginator(queryset, self.page_size)

        try:
            self.page = self.paginator.page(self.page_number)
            return list(self.page)
        except EmptyPage:
            return []

    def get_paginated_response(self, data: List[Dict]) -> Response:
        """
        Return optimized paginated response with metadata
        """
        response_data = self._build_response_data(data)

        # Cache the page if not explicitly bypassed
        if not self._should_bypass_cache():
            self._cache_current_page(response_data)

        return Response(response_data)

    def _get_page_number(self, request) -> int:
        """Get and validate page number"""
        try:
            page = int(request.query_params.get(self.page_query_param, 1))
            return max(1, page)
        except (ValueError, TypeError):
            return 1

    def _get_page_size(self, request) -> int:
        """Get and validate page size"""
        try:
            page_size = int(
                request.query_params.get(self.page_size_query_param, self.page_size)
            )
            return min(max(1, page_size), self.max_page_size)
        except (ValueError, TypeError):
            return self.page_size

    def _get_cached_count(self, queryset, request) -> int:
        """
        Get total count with caching, using a cache key based on query parameters
        """
        cache_key = self._build_count_cache_key(queryset, request)
        cached_count = get_cached_value(cache_key)

        if cached_count is not None:
            try:
                return int(cached_count)
            except Exception:
                return cached_count

        # Use optimized count for large datasets
        count = self._get_optimized_count(queryset)

        # Cache the count
        set_cached_value(cache_key, count, timeout=self.count_cache_timeout)
        return count

    def _get_optimized_count(self, queryset) -> int:
        """
        Get count with optimizations for different database backends
        """
        # For large datasets, use approximate count if available
        try:
            # Try to use faster counting methods
            if hasattr(queryset, "count"):
                return queryset.count()
            else:
                return len(queryset)
        except Exception:
            # Fallback to basic count
            return queryset.count()

    def _build_count_cache_key(self, queryset, request) -> str:
        """
        Build a unique cache key for count based on query parameters
        """
        base_key = f"csv_count:{queryset.model._meta.model_name}"

        # Include relevant query parameters in cache key
        params = [
            request.GET.get("search", ""),
            request.GET.get("filters", ""),
            str(queryset.query.where),  # Include WHERE clause fingerprint
        ]

        param_hash = hash(tuple(params))
        return f"{base_key}:{param_hash}"

    def _build_response_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Build the complete paginated response structure"""
        return {
            "data": data,
            "pagination": self._get_pagination_metadata(),
            "performance": self._get_performance_metadata(),
        }

    def _get_pagination_metadata(self) -> Dict[str, Any]:
        """Get comprehensive pagination metadata"""
        total_pages = (
            math.ceil(self.total_count / self.page_size) if self.total_count > 0 else 0
        )

        return {
            "current_page": self.page_number,
            "page_size": self.page_size,
            "total_count": self.total_count,
            "total_pages": total_pages,
            "has_next": self.page_number < total_pages if total_pages > 0 else False,
            "has_prev": self.page_number > 1,
            "next_page": (
                self.page_number + 1 if self.page_number < total_pages else None
            ),
            "prev_page": self.page_number - 1 if self.page_number > 1 else None,
            "range_start": ((self.page_number - 1) * self.page_size) + 1,
            "range_end": min(self.page_number * self.page_size, self.total_count),
        }

    def _get_performance_metadata(self) -> Dict[str, Any]:
        """Get performance metadata"""
        return {
            "cached": False,  # Will be set by caching logic
        }

    def _cache_current_page(self, response_data: Dict[str, Any]):
        """Cache the current page response"""
        cache_key = self._build_page_cache_key()
        set_cached_value(cache_key, response_data, timeout=self.page_cache_timeout)

    def _build_page_cache_key(self) -> str:
        """Build a unique cache key for the current page"""
        model_name = "unknown"
        try:
            if self.queryset is not None and hasattr(self.queryset, "model"):
                model_name = getattr(self.queryset.model._meta, "model_name", "unknown")
        except Exception:
            model_name = "unknown"

        base_key = f"csv_page:{model_name}"

        # Safely read request params (self.request may be None in some contexts)
        search_val = ""
        filters_val = ""
        sort_val = ""
        columns_val = ""
        try:
            if self.request is not None:
                search_val = self.request.GET.get("search", "")
                filters_val = self.request.GET.get("filters", "")
                sort_val = self.request.GET.get("sort_by", "")
                columns_val = self.request.GET.get("columns", "")
        except Exception:
            pass

        params = {
            "page": self.page_number,
            "page_size": self.page_size,
            "search": search_val,
            "filters": filters_val,
            "sort": sort_val,
            "columns": columns_val,
        }

        param_hash = hash(frozenset(params.items()))
        return f"{base_key}:{param_hash}"

    def _should_bypass_cache(self) -> bool:
        """Check if caching should be bypassed"""
        try:
            if not self.request:
                return False
            return self.request.GET.get("nocache", "false").lower() == "true"
        except Exception:
            return False


class CSVStreamingPagination(CSVPagination):
    """
    Streaming pagination for very large datasets - returns data in chunks
    """

    streaming_page_size = 1000  # Larger page size for streaming

    def paginate_queryset(self, queryset, request, view=None):
        """
        Stream pagination that doesn't load all data at once
        """
        self.request = request
        self.queryset = queryset

        self.page_number = self._get_page_number(request)
        self.page_size = self._get_streaming_page_size(request)
        self.total_count = self._get_cached_count(queryset, request)

        # Use database-level pagination for better performance
        start_idx = (self.page_number - 1) * self.page_size
        end_idx = start_idx + self.page_size

        return list(queryset[start_idx:end_idx])

    def _get_streaming_page_size(self, request) -> int:
        """Get page size for streaming (can be larger)"""
        try:
            page_size = int(
                request.query_params.get(
                    self.page_size_query_param, self.streaming_page_size
                )
            )
            return min(max(100, page_size), 5000)  # Allow larger pages for streaming
        except (ValueError, TypeError):
            return self.streaming_page_size


class CSVCursorPagination(BasePagination):
    """
    Cursor-based pagination for infinite scrolling and consistent ordering
    """

    page_size = 100
    max_page_size = 500
    ordering = "id"
    cursor_query_param = "cursor"

    def __init__(self):
        self.request = None
        self.queryset = None
        self.cursor = None
        self.has_next = None
        self.has_previous = None

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.queryset = queryset.order_by(self.ordering)
        self.cursor = self.decode_cursor(request)

        if self.cursor:
            # Filter queryset based on cursor position
            queryset = queryset.filter(id__gt=self.cursor)

        page = list(
            queryset[: self.page_size + 1]
        )  # Get one extra to check for next page

        self.has_next = len(page) > self.page_size
        self.has_previous = self.cursor is not None

        if self.has_next:
            page = page[:-1]  # Remove the extra item

        return page

    def get_paginated_response(self, data):
        next_cursor = None
        previous_cursor = None

        if data:
            # data items should include 'row_id' or 'id' depending on shape; expect 'row_id'
            next_cursor = data[-1].get("row_id") if self.has_next else None
            previous_cursor = (
                (data[0].get("row_id") - self.page_size - 1)
                if self.has_previous
                else None
            )

        return Response(
            {
                "data": data,
                "pagination": {
                    "next_cursor": next_cursor,
                    "previous_cursor": previous_cursor,
                    "has_next": self.has_next,
                    "has_previous": self.has_previous,
                    "page_size": self.page_size,
                },
            }
        )

    def decode_cursor(self, request):
        cursor = request.query_params.get(self.cursor_query_param)
        if cursor:
            try:
                return int(cursor)
            except (ValueError, TypeError):
                return None
        return None
