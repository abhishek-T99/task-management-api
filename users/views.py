from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .serializers import (
    UserRegisterSerializer,
    UserRetrieveSerializer,
    UserLoginSerializer,
)
from drf_yasg.utils import swagger_auto_schema
from logging import getLogger

logger = getLogger(__name__)


@swagger_auto_schema(
    method="post",
    request_body=UserRegisterSerializer,
    responses={201: UserRetrieveSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # Create Token
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            UserRetrieveSerializer(user).data, status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method="post",
    request_body=UserLoginSerializer,
    responses={201: "Successfully Logged in."},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"detail": "Email and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, email=email, password=password)
    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {"detail": "Succesfully Logged in.", "token": token.key},
            status=status.HTTP_200_OK,
        )
    return Response(
        {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
    )


@swagger_auto_schema(method="get", responses={201: UserRetrieveSerializer})
@api_view(["GET"])
@permission_classes(
    [
        IsAuthenticated,
    ]
)
def get_current_user(request):
    serializer = UserRetrieveSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)
