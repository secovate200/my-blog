"""느린 이메일 발송을 HTTP 요청 처리와 분리하고 실패를 안전하게 기록합니다.

호출부가 실행 방식을 알지 않게 하여 추후 외부 작업 큐로 교체할 때 뷰와
서비스 계층을 수정하지 않아도 되도록 합니다.
"""

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
            "문의 %s가 %s 알림 작업 실행 전에 삭제되었습니다.",
            contact_id,
            notification_name,
        )
    except Exception:
        logger.exception(
            "%s 알림 발송 중 문의 %s에서 예기치 않은 오류가 발생했습니다.",
            notification_name,
            contact_id,
        )
    finally:
        close_old_connections()


def enqueue_contact_notifications(contact_id):
    """HTTP 응답을 지연시키지 않고 외부 문의 알림을 발송합니다."""
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
        "접수 확인 이메일",
    )


def _run_contact_reply(contact_id, replied_by_id):
    close_old_connections()
    try:
        contact = ContactMessage.objects.get(pk=contact_id)
        if not send_contact_reply(contact):
            logger.warning("문의 %s의 답변 이메일 발송에 실패했습니다.", contact_id)
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
            "문의 %s가 답변 이메일 작업 실행 전에 삭제되었습니다.",
            contact_id,
        )
    except Exception:
        logger.exception(
            "문의 %s의 답변 이메일 발송 중 예기치 않은 오류가 발생했습니다.",
            contact_id,
        )
    finally:
        close_old_connections()


def enqueue_contact_reply(contact_id, replied_by_id):
    """관리자 응답을 지연시키지 않고 저장된 문의 답변을 발송합니다."""
    _notification_executor.submit(_run_contact_reply, contact_id, replied_by_id)


def _run_user_notification(user_id, sender, notification_name):
    close_old_connections()
    try:
        user = get_user_model().objects.get(pk=user_id)
        sender(user)
    except get_user_model().DoesNotExist:
        logger.warning(
            "사용자 %s가 %s 알림 작업 실행 전에 삭제되었습니다.",
            user_id,
            notification_name,
        )
    except Exception:
        logger.exception(
            "%s 알림 발송 중 사용자 %s에서 예기치 않은 오류가 발생했습니다.",
            notification_name,
            user_id,
        )
    finally:
        close_old_connections()


def enqueue_signup_notification(user_id):
    """HTTP 응답을 지연시키지 않고 관리자에게 신규 가입을 알립니다."""
    _notification_executor.submit(
        _run_user_notification,
        user_id,
        send_signup_notification,
        "신규 가입 Discord",
    )


def enqueue_account_approval_email(user_id):
    """관리자 저장 요청을 지연시키지 않고 계정 승인 이메일을 발송합니다."""
    _notification_executor.submit(
        _run_user_notification,
        user_id,
        send_account_approval_email,
        "계정 승인 이메일",
    )
