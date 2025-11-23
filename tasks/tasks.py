from __future__ import annotations
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from .models import Task


@shared_task(bind=True)
def send_task_completed_email(self, task_id: str) -> None:
    try:
        task = Task.objects.select_related("user").get(pk=task_id)
    except Task.DoesNotExist:
        return

    user = task.user
    subject = f"Task completed: {task.title}"
    context = {"user": user, "task": task}

    plain = render_to_string("emails/task_completed.txt", context)
    html = render_to_string("emails/task_completed.html", context)

    msg = EmailMultiAlternatives(
        subject, plain, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)
