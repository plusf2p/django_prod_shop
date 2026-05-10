from typing import Sequence
from celery import shared_task
# from celery.utils.log import get_task_logger

from django.core.mail import send_mail


# logger = get_task_logger(__name__)

@shared_task
def send_email_task(subject: str, body: str, to: Sequence[str]) -> None:
    send_mail(
        subject=subject,
        message=body,
        from_email=None,
        recipient_list=list(to),
        fail_silently=False,
    )
