from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Task
from .serializers import TaskSerializer
from .pagination import TaskPagination


priority_param = openapi.Parameter(
    "priority",
    openapi.IN_QUERY,
    description="Filter tasks by priority (low, medium, high)",
    type=openapi.TYPE_STRING,
)

status_param = openapi.Parameter(
    "status",
    openapi.IN_QUERY,
    description="Filter tasks by status (pending, in_progress, completed)",
    type=openapi.TYPE_STRING,
)


@swagger_auto_schema(
    method="get",
    manual_parameters=[priority_param, status_param],
)
@swagger_auto_schema(
    method="post",
    request_body=TaskSerializer,
    responses={201: TaskSerializer},
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def task_list_create(request):
    user = request.user

    if request.method == "GET":
        tasks = Task.objects.filter(user=user)

        # Filtering
        priority = request.GET.get("priority")
        status_value = request.GET.get("status")

        if priority:
            tasks = tasks.filter(priority=priority)

        if status_value:
            tasks = tasks.filter(status=status_value)

        # Pagination
        paginator = TaskPagination()
        paginated_tasks = paginator.paginate_queryset(tasks, request)

        response_serializer = TaskSerializer(paginated_tasks, many=True)
        return paginator.get_paginated_response(response_serializer.data)

    elif request.method == "POST":
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save(user=user)
            response_serializer = TaskSerializer(task)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method="get",
    parameters=[
        openapi.Parameter(
            "pk",
            openapi.IN_PATH,
            description="ID of the task to retrieve",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
        )
    ],
    responses={200: TaskSerializer},
)
@swagger_auto_schema(
    method="patch",
    parameters=[
        openapi.Parameter(
            "pk",
            openapi.IN_PATH,
            description="ID of the task to update",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
        )
    ],
    request_body=TaskSerializer,
    responses={200: TaskSerializer},
)
@swagger_auto_schema(
    method="delete",
    parameters=[
        openapi.Parameter(
            "pk",
            openapi.IN_PATH,
            description="ID of the task to delete",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
        )
    ],
    responses={204: "No content"},
)
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def task_detail(request, pk):
    user = request.user

    try:
        task = Task.objects.get(pk=pk, user=user)
    except Task.DoesNotExist:
        return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = TaskSerializer(task)
        return Response(TaskSerializer(serializer.data).data)

    elif request.method == "PATCH":
        serializer = TaskSerializer(task, data=request.data, partial=request.method)
        if serializer.is_valid():
            serializer.save()
            return Response(TaskSerializer(serializer.data).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
