from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import UserAccessStatus
from .tasks import enqueue_account_approval_email


@receiver(post_save, sender=get_user_model())
def create_user_access_status(sender, instance, created, **kwargs):
    if created:
        UserAccessStatus.objects.get_or_create(
            user=instance,
            defaults={"status": UserAccessStatus.Status.APPROVED},
        )


@receiver(pre_save, sender=UserAccessStatus)
def remember_previous_access_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = sender.objects.filter(pk=instance.pk).values_list(
        "status", flat=True
    ).first()


@receiver(post_save, sender=UserAccessStatus)
def notify_user_when_approved(sender, instance, created, **kwargs):
    if (
        not created
        and instance.status == UserAccessStatus.Status.APPROVED
        and getattr(instance, "_previous_status", None) != UserAccessStatus.Status.APPROVED
    ):
        transaction.on_commit(
            lambda: enqueue_account_approval_email(instance.user_id)
        )
