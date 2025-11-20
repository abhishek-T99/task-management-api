from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("full_name", "email", "password", "password_confirm")
        optional_fields = [
            "full_name",
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email address already taken.")
        return value.lower().strip()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )

        return attrs

    def create(self, validated_data):
        if validated_data.get("full_name") is None:
            validated_data["full_name"] = None
        user = User.objects.create(
            email=validated_data["email"],
            full_name=validated_data["full_name"],
        )
        email_username, _ = user.email.split("@")
        user.username = email_username

        user.set_password(validated_data["password"])
        user.save()
        return user


class UserRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "full_name", "email", "username")


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
