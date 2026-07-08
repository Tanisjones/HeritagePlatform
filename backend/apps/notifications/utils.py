import logging

from django.core.mail import send_mail
from django.template import Context, Template
from .models import NotificationTemplate

logger = logging.getLogger(__name__)


def send_notification_email(template_name, recipient_email, context_data):
    """
    Sends an email based on a notification template. Best-effort: a broken or
    unconfigured mail backend must NEVER break the state change that triggered
    the notification (e.g. publishing an item), so all failures are logged and
    swallowed.
    """
    try:
        template = NotificationTemplate.objects.get(name=template_name)
    except NotificationTemplate.DoesNotExist:
        # Handle template not found error
        return

    context = Context(context_data)
    subject_template = Template(template.subject)
    body_template = Template(template.body)

    subject = subject_template.render(context)
    body = body_template.render(context)

    try:
        send_mail(
            subject,
            body,
            None,  # Uses DEFAULT_FROM_EMAIL from settings
            [recipient_email],
            html_message=body if template.is_html else None,
        )
    except Exception:  # noqa: BLE001 — email is best-effort, never fatal
        logger.exception(
            "Failed to send notification email (template=%s, recipient=%s)",
            template_name,
            recipient_email,
        )
