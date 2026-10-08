import logging
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.utils import timezone

from .models import ContactMessage
from .notifications import (
    send_account_approval_email,
    send_contact_notification,
    send_contact_receipt,
    send_contact_reply,
    send_signup_notification,
)


logger = logging.getLogger(__name__)
_notification_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="contact-notification",
)


def _run_contact_notification(contact_id, sender, notification_name):
    close_old_connections()
    try:
        contact = ContactMessage.objects.get(pk=contact_id)
        sender(contact)
    except ContactMessage.DoesNotExist:
        logger.warning(
            "Contact %s disappeared before the %s notification ran",
            contact_id,
            notification_name,
        )
    except Exception:
        logger.exception(
            "Unexpected failure while sending the %s notification for contact %s",
            notification_name,
            contact_id,
        )
    finally:
        close_old_connections()


def enqueue_contact_notifications(contact_id):
    """Send external contact notifications without blocking the HTTP response."""
    _notification_executor.submit(
        _run_contact_notification,
        contact_id,
        send_contact_notification,
        "Discord",
    )
    _notification_executor.submit(
        _run_contact_notification,
        contact_id,
        send_contact_receipt,
        "receipt email",
    )


def _run_contact_reply(contact_id, replied_by_id):
    close_old_connections()
    try:
        contact = ContactMessage.objects.get(pk=contact_id)
        if not send_contact_reply(contact):
            logger.warning("Contact reply email failed for contact %s", contact_id)
            return

        sent_at = timezone.now()
        ContactMessage.objects.filter(pk=contact_id).update(
            status=ContactMessage.Status.REPLIED,
            replied_by_id=replied_by_id,
            replied_at=sent_at,
            email_sent_at=sent_at,
        )
    except ContactMessage.DoesNotExist:
        logger.warning(
            "Contact %s disappeared before the reply email ran",
            contact_id,
        )
    except Exception:
        logger.exception(
            "Unexpected failure while sending the reply email for contact %s",
            contact_id,
        )
    finally:
        close_old_connections()


def enqueue_contact_reply(contact_id, replied_by_id):
    """Send a saved admin reply without blocking the admin response."""
    _notification_executor.submit(_run_contact_reply, contact_id, replied_by_id)


def _run_user_notification(user_id, sender, notification_name):
    close_old_connections()
    try:
        user = get_user_model().objects.get(pk=user_id)
        sender(user)
    except get_user_model().DoesNotExist:
        logger.warning(
            "User %s disappeared before the %s notification ran",
            user_id,
            notification_name,
        )
    except Exception:
        logger.exception(
            "Unexpected failure while sending the %s notification for user %s",
            notification_name,
            user_id,
        )
    finally:
        close_old_connections()


def enqueue_signup_notification(user_id):
    """Notify administrators of a signup without blocking the HTTP response."""
    _notification_executor.submit(
        _run_user_notification,
        user_id,
        send_signup_notification,
        "signup Discord",
    )


def enqueue_account_approval_email(user_id):
    """Send the approval email without blocking the admin save request."""
    _notification_executor.submit(
        _run_user_notification,
        user_id,
        send_account_approval_email,
        "account approval email",
    )
