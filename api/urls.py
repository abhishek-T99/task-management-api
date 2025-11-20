from django.urls import path
from api import views as api_views

urlpatterns = [
    path("health-check/", api_views.health_check, name="health_check"),
]
