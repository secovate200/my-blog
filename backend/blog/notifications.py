import json
import logging
import smtplib
from email.mime.image import MIMEImage
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.utils import timezone


logger = logging.getLogger(__name__)
LOGO_PATH = Path(settings.BASE_DIR) / "static" / "email" / "logo.png"


def attach_inline_logo(email):
    logo = MIMEImage(LOGO_PATH.read_bytes(), _subtype="png")
    logo.add_header("Content-ID", "<secovate200-logo>")
    logo.add_header("Content-Disposition", "inline", filename="logo.png")
    email.attach(logo)


def send_contact_notification(contact):
    """새 문의를 Discord로 알립니다. 미설정·전송 실패는 문의 저장에 영향을 주지 않습니다."""
    webhook_url = settings.DISCORD_WEBHOOK_URL
    if not webhook_url:
        return False

    payload = {
        "username": "My Blog Contact",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "새 문의가 도착했습니다",
                "color": 0x5865F2,
                "fields": [
                    {"name": "이름", "value": contact.name, "inline": True},
                    {"name": "이메일", "value": contact.email, "inline": True},
                    {"name": "내용", "value": contact.message[:1000]},
                ],
                "footer": {"text": f"문의 #{contact.pk}"},
                "timestamp": contact.created_at.isoformat(),
            }
        ],
    }
    request = Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "my-blog/1.0"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        logger.exception("Discord contact notification failed for contact %s", contact.pk)
        return False


def send_signup_notification(user):
    """신규 회원가입 승인 요청을 Discord 관리자 채널로 알립니다."""
    webhook_url = settings.DISCORD_SIGNUP_WEBHOOK_URL
    if not webhook_url:
        return False

    payload = {
        "username": "My Blog Account",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "새 회원가입 승인 요청",
                "color": 0xF0A020,
                "fields": [
                    {"name": "이름", "value": user.get_full_name() or "-", "inline": True},
                    {"name": "이메일", "value": user.email, "inline": True},
                    {"name": "상태", "value": "승인 대기", "inline": True},
                ],
                "footer": {"text": f"사용자 #{user.pk}"},
                "timestamp": timezone.now().isoformat(),
            }
        ],
    }
    request = Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "my-blog/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        logger.exception("Discord signup notification failed for user %s", user.pk)
        return False


def send_account_approval_email(user):
    """관리자 승인이 완료된 사용자에게 로그인 가능 상태를 안내합니다."""
    if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL or not user.email:
        return False

    name = escape(user.get_full_name() or user.email)
    login_url = escape(settings.DASHBOARD_LOGIN_URL)
    subject = "[SECOVATE200 BLOG] 계정 승인이 완료되었습니다"
    text_body = (
        f"{user.get_full_name() or user.email}님, 안녕하세요.\n\n"
        "회원가입 승인이 완료되어 이제 대시보드에 로그인할 수 있습니다.\n"
        f"로그인: {settings.DASHBOARD_LOGIN_URL}\n\n"
        "SECOVATE200 BLOG"
    )
    html_body = f"""
    <!doctype html>
    <html lang="ko">
      <body style="margin:0;background:#f4f5f7;font-family:Arial,'Noto Sans KR',sans-serif;color:#20242a;">
        <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
          <div style="background:#ffffff;border:1px solid #e4e7eb;padding:36px;text-align:center;">
            <img src="cid:secovate200-logo" alt="SECOVATE200 로고" width="120"
                 style="display:block;width:120px;height:auto;margin:0 auto 24px;">
            <p style="margin:0 0 8px;color:#22a06b;font-size:12px;letter-spacing:2px;">ACCOUNT APPROVED</p>
            <h1 style="margin:0 0 20px;font-size:24px;line-height:1.4;">계정 승인이 완료되었습니다</h1>
            <p style="margin:0 0 22px;font-size:15px;line-height:1.8;">{name}님, 이제 대시보드에 로그인할 수 있습니다.</p>
            <a href="{login_url}" style="display:inline-block;padding:13px 24px;background:#20242a;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:bold;">로그인하기</a>
          </div>
          <p style="margin:18px 0 0;text-align:center;color:#98a2b3;font-size:11px;">SECOVATE200 BLOG</p>
        </div>
      </body>
    </html>
    """
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_body, "text/html")
    try:
        attach_inline_logo(email)
        email.send(fail_silently=False)
        return True
    except (BadHeaderError, OSError, smtplib.SMTPException, ValueError):
        logger.exception("Account approval email failed for user %s", user.pk)
        return False

def send_contact_receipt(contact):
    """문의자에게 로고가 포함된 접수 확인 메일을 보냅니다."""
    if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:
        return False

    name = escape(contact.name)
    subject = f"[SECOVATE200 BLOG] 문의 #{contact.pk}가 접수되었습니다"
    text_body = (
        f"{contact.name}님, 안녕하세요.\n\n"
        f"문의 #{contact.pk}가 정상적으로 접수되었습니다.\n"
        "내용을 확인한 뒤 입력해 주신 이메일로 답변드리겠습니다.\n\n"
        "SECOVATE200 BLOG"
    )
    html_body = f"""
    <!doctype html>
    <html lang="ko">
      <body style="margin:0;background:#f4f5f7;font-family:Arial,'Noto Sans KR',sans-serif;color:#20242a;">
        <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
          <div style="background:#ffffff;border:1px solid #e4e7eb;padding:36px;text-align:center;">
            <img src="cid:secovate200-logo" alt="SECOVATE200 로고" width="120"
                 style="display:block;width:120px;height:auto;margin:0 auto 24px;">
            <p style="margin:0 0 8px;color:#5865f2;font-size:12px;letter-spacing:2px;">CONTACT RECEIVED</p>
            <h1 style="margin:0 0 20px;font-size:24px;line-height:1.4;">문의가 정상 접수되었습니다</h1>
            <p style="margin:0 0 12px;font-size:15px;line-height:1.8;">{name}님, 메시지를 보내주셔서 감사합니다.</p>
            <p style="margin:0;font-size:14px;line-height:1.8;color:#667085;">
              문의 번호는 <strong>#{contact.pk}</strong>입니다.<br>
              확인 후 입력해 주신 이메일로 답변드리겠습니다.
            </p>
          </div>
          <p style="margin:18px 0 0;text-align:center;color:#98a2b3;font-size:11px;">SECOVATE200 BLOG</p>
        </div>
      </body>
    </html>
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[contact.email],
    )
    email.attach_alternative(html_body, "text/html")

    try:
        attach_inline_logo(email)
        email.send(fail_silently=False)
        contact.receipt_sent_at = timezone.now()
        contact.save(update_fields=["receipt_sent_at"])
        return True
    except (BadHeaderError, OSError, smtplib.SMTPException, ValueError):
        logger.exception("Contact receipt email failed for contact %s", contact.pk)
        return False


def send_contact_reply(contact):
    """관리자가 작성한 답변을 문의자의 이메일로 전송합니다."""
    if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL or not contact.reply.strip():
        return False

    name = escape(contact.name)
    message_html = escape(contact.message).replace("\n", "<br>")
    reply_html = escape(contact.reply).replace("\n", "<br>")
    subject = f"[SECOVATE200 BLOG] 문의 #{contact.pk}에 답변드립니다"
    text_body = (
        f"{contact.name}님, 안녕하세요.\n\n"
        f"문의 #{contact.pk}에 대한 답변입니다.\n\n"
        f"[문의 내용]\n{contact.message}\n\n"
        f"[답변 내용]\n{contact.reply}\n\n"
        "SECOVATE200 BLOG"
    )
    html_body = f"""
    <!doctype html>
    <html lang="ko">
      <body style="margin:0;background:#f4f5f7;font-family:Arial,'Noto Sans KR',sans-serif;color:#20242a;">
        <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
          <div style="background:#ffffff;border:1px solid #e4e7eb;padding:36px;">
            <img src="cid:secovate200-logo" alt="SECOVATE200 로고" width="120"
                 style="display:block;width:120px;height:auto;margin:0 auto 24px;">
            <p style="margin:0 0 8px;text-align:center;color:#5865f2;font-size:12px;letter-spacing:2px;">CONTACT REPLY</p>
            <h1 style="margin:0 0 24px;text-align:center;font-size:24px;line-height:1.4;">문의에 답변드립니다</h1>
            <p style="margin:0 0 18px;font-size:15px;line-height:1.8;">{name}님, 안녕하세요.</p>
            <p style="margin:0 0 8px;color:#667085;font-size:12px;font-weight:bold;">문의 내용</p>
            <div style="margin-bottom:22px;padding:20px;background:#f8f9fb;border-left:3px solid #98a2b3;font-size:14px;line-height:1.9;color:#475467;">
              {message_html}
            </div>
            <p style="margin:0 0 8px;color:#5865f2;font-size:12px;font-weight:bold;">답변 내용</p>
            <div style="padding:20px;background:#f8f9fb;border-left:3px solid #5865f2;font-size:14px;line-height:1.9;">
              {reply_html}
            </div>
            <p style="margin:20px 0 0;color:#667085;font-size:12px;">문의 번호 #{contact.pk}</p>
          </div>
          <p style="margin:18px 0 0;text-align:center;color:#98a2b3;font-size:11px;">SECOVATE200 BLOG</p>
        </div>
      </body>
    </html>
    """
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[contact.email],
    )
    email.attach_alternative(html_body, "text/html")

    try:
        attach_inline_logo(email)
        email.send(fail_silently=False)
        return True
    except (BadHeaderError, OSError, smtplib.SMTPException, ValueError):
        logger.exception("Contact reply email failed for contact %s", contact.pk)
        return False
