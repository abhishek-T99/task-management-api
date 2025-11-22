from __future__ import annotations
from uuid import UUID
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from .models import User


@shared_task
def send_welcome_email(user_id: UUID) -> None:
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    subject = "Welcome to Task Management"
    context = {"user": user}

    # Render both plain text and HTML versions
    plain = render_to_string("emails/welcome.txt", context)
    html = render_to_string("emails/welcome.html", context)

    msg = EmailMultiAlternatives(
        subject, plain, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)
