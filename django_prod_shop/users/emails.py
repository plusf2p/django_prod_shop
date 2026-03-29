from django.db import transaction
from djoser.email import ActivationEmail, PasswordResetEmail

from django_prod_shop.users.tasks import send_email_task


class CeleryActivationEmail(ActivationEmail):
    def send(self, to, *args, **kwargs):
        self.render()

        transaction.on_commit(
            lambda: send_email_task.delay(
                subject=self.subject,
                body=self.body,
                to=list(to),
            )
        )

        return 1


class CeleryPasswordResetEmail(PasswordResetEmail):
    def send(self, to, *args, **kwargs):
        self.render()

        transaction.on_commit(
            lambda: send_email_task.delay(
                subject=self.subject,
                body=self.body,
                to=list(to),
            )
        )

        return 1
