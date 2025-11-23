import logging
from celery import current_app as celery_app
from celery.exceptions import CeleryError
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from django.db import connection
from django_redis import get_redis_connection
import os
from datetime import datetime
import psutil

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes(
    [
        AllowAny,
    ]
)
def health_check(request):
    logger.info("Health check running...")

    # Initialize health status
    overall_status = "healthy"
    checks = {}

    # Database Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = {
                "status": "healthy",
                "details": "Database connection successful",
            }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        checks["database"] = {
            "status": "unhealthy",
            "details": f"Database connection failed: {str(e)}",
        }
        overall_status = "degraded"

    # Redis Cache Check
    try:
        redis_client = get_redis_connection("default")
        redis_response = redis_client.ping()
        if redis_response:
            checks["redis"] = {
                "status": "healthy",
                "details": "Redis cache connection successful",
            }
        else:
            checks["redis"] = {
                "status": "unhealthy",
                "details": "Redis ping failed",
            }
            overall_status = "degraded"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        checks["redis"] = {
            "status": "unhealthy",
            "details": f"Redis connection failed: {str(e)}",
        }
        overall_status = "degraded"

    # Celery Health Check
    try:
        ping = celery_app.control.ping(timeout=1.0)
        if ping:
            checks["celery"] = {
                "status": "healthy",
                "details": "Celery worker detected",
            }
        else:
            checks["celery"] = {
                "status": "unhealthy",
                "details": "No Celery workers responded",
            }
            overall_status = "degraded"
    except CeleryError as e:
        logger.error(f"Celery health check failed: {str(e)}")
        checks["celery"] = {"status": "unhealthy", "details": str(e)}
        overall_status = "degraded"

    # System Resources
    try:
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB

        checks["system"] = {
            "status": "healthy",
            "details": {
                "memory_usage_mb": round(memory_usage, 2),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "disk_usage": psutil.disk_usage("/").percent,
            },
        }
    except Exception as e:
        logger.warning(f"System metrics check failed: {str(e)}")
        checks["system"] = {
            "status": "unknown",
            "details": f"System metrics unavailable: {str(e)}",
        }

    # Overall response
    health_data = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "service": "Task Management API",
        "version": "1.0.0",
        "checks": checks,
    }

    # Log health status
    if overall_status == "healthy":
        logger.info("Health check completed - all systems healthy")
    else:
        logger.warning(f"Health check completed - status: {overall_status}")

    return Response(health_data)
