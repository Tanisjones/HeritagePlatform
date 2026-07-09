import logging

from django.core.mail import send_mail
from django.template import Context, Template
from .models import NotificationTemplate, UserNotification

logger = logging.getLogger(__name__)


def notify_city_curators(
    city_id,
    notification_type,
    title,
    message,
    content_object=None,
    exclude_user_id=None,
):
    """
    In-app broadcast to every curator of a city (per-city CityRole grants).
    `exclude_user_id` keeps a curator from being notified about their own
    action. Staff are not included — they monitor the admin, not the bell.
    """
    from apps.cities.models import CityRole

    if not city_id:
        return
    curator_ids = set(
        CityRole.objects.filter(
            city_id=city_id, role=CityRole.ROLE_CURATOR
        ).values_list('user_id', flat=True)
    )
    curator_ids.discard(exclude_user_id)
    for user_id in curator_ids:
        UserNotification.objects.create(
            recipient_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            content_object=content_object,
        )


def notify_queue_arrival(item, resubmitted=False):
    """
    D3 — tell a city's curators that a contribution landed in their queue
    (new submission, draft sent to review, or resubmission after changes).
    Contributors already get outcome notifications; this is the arrival side.
    """
    city_name = item.city.name if item.city_id else ''
    if resubmitted:
        message = f'«{item.title}» fue reenviada a revisión en {city_name}.'
    else:
        message = f'«{item.title}» espera revisión en {city_name}.'
    notify_city_curators(
        item.city_id,
        'moderation_needed',
        'Nueva contribución en la cola',
        message,
        content_object=item,
        exclude_user_id=item.contributor_id,
    )


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
