import logging
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from environ import Env

env = Env()
env.read_env()

logger = logging.getLogger(__name__)

schema_view = get_schema_view(
    openapi.Info(
        title="Task Management APIs",
        default_version="v1",
        description="This is the API documentation for Task Managment APIs",
        terms_of_service="https://www.google.com/policies/terms/",
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "api/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    path("api/v1/", include("api.urls")),
    path("admin/", admin.site.urls),
]

# if settings.DEBUG:
#     urlpatterns += [
#         path("__debug__/", include("debug_toolbar.urls")),
#     ]
