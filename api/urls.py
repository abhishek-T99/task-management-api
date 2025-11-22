from django.urls import path
from api import views as api_views
from users import views as user_views
from tasks import views as task_views

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
]
