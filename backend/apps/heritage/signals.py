from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import HeritageItem
from apps.notifications.utils import send_notification_email


@receiver(pre_save, sender=HeritageItem)
def send_status_change_notification_on_update(sender, instance, **kwargs):
    if instance.pk:  # if the object is not new
        try:
            old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return  # Should not happen

        if old_instance.status != instance.status and instance.contributor:
            context = {
                'heritage_item_title': instance.title,
                'new_status': instance.get_status_display(),
                'moderator_feedback': instance.moderator_feedback,
            }
            if instance.status == 'published':
                send_notification_email(
                    'contribution-published',
                    instance.contributor.email,
                    context,
                )
            elif instance.status == 'rejected':
                send_notification_email(
                    'contribution-rejected',
                    instance.contributor.email,
                    context,
                )