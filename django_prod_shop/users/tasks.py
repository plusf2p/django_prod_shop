import uuid

from celery import shared_task
from celery.utils.log import get_task_logger

from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings


logger = get_task_logger(__name__)


@shared_task
def send_reset_password_email(email, request):
    reset_uuid = uuid.UUID()
    reset_url = request.build_absolute_uri(reverse('users:reset_password', kwargs={'uuid': reset_uuid}))
    text = f'Чтобы восстановить пароль перейдите по ссылке:\n\n{reset_url}'\
        f'\n\nЕсли это сделали не вы, просто проигнорируйте сообщение.'

    # logger.info(1)

    send_mail(
        subject=f'Восстановление пароля в магазине "{settings.SHOP_NAME}"',
        message=text,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )
