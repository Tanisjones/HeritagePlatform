from django.core.mail import send_mail
from django.template import Context, Template
from .models import NotificationTemplate


def send_notification_email(template_name, recipient_email, context_data):
    """
    Sends an email based on a notification template.
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

    send_mail(
        subject,
        body,
        None,  # Uses DEFAULT_FROM_EMAIL from settings
        [recipient_email],
        html_message=body if template.is_html else None,
    )
