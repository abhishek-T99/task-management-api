from django.urls import path
from api import views as api_views
from users import views as user_views
from tasks import views as task_views
from csv_processor import views as csv_views

urlpatterns = [
    # Health Check URL
    path("health-check/", api_views.health_check, name="health_check"),
    # User URLs
    path("auth/user/register/", user_views.register_user, name="register_user"),
    path("auth/user/login/", user_views.login_user, name="login_user"),
    path("auth/user/me/", user_views.get_current_user, name="logged_in_user"),
    path("auth/user/logout/", user_views.logout, name="logout_user"),
    # Task URLs
    path("tasks/", task_views.task_list_create, name="task_list_create"),
    path("tasks/<uuid:pk>/", task_views.task_detail, name="task_detail"),
    # CSV Processor URLs
    path(
        "csv-data/uploads/",
        csv_views.csv_upload_list_create,
        name="csv-upload-list-create",
    ),
    path(
        "csv-data/uploads/<uuid:upload_id>/",
        csv_views.csv_upload_detail,
        name="csv-upload-detail",
    ),
    path(
        "csv-data/uploads/<uuid:upload_id>/progress/",
        csv_views.csv_upload_progress,
        name="csv-upload-progress",
    ),
    path(
        "csv-data/uploads/<uuid:upload_id>/data/",
        csv_views.csv_upload_data,
        name="csv-upload-data",
    ),
    path(
        "csv-data/uploads/<uuid:upload_id>/delete/",
        csv_views.csv_upload_delete,
        name="csv-upload-delete",
    ),
]
