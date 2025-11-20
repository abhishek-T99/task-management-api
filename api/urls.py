from django.urls import path
from api import views as api_views
from users import views as user_views

urlpatterns = [
    # Health Check URL
    path("health-check/", api_views.health_check, name="health_check"),
    # User URLs
    path("user/register/", user_views.register_user, name="register_user"),
    path("user/login/", user_views.login_user, name="login_user"),
    path("user/me/", user_views.get_current_user, name="logged_in_user"),
]
