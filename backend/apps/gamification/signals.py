from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.heritage.models import Annotation
from apps.routes.models import UserRouteProgress
from .services import handle_annotation_created, handle_route_completed


@receiver(post_save, sender=Annotation)
def award_points_for_annotation(sender, instance, created, **kwargs):
    """
    Grant points when an annotation is created.
    """
    if created:
        handle_annotation_created(instance)


@receiver(post_save, sender=UserRouteProgress)
def award_points_for_route_completion(sender, instance, **kwargs):
    """
    Grant points when a user completes a route.
    """
    if instance.completed_at:
        handle_route_completed(instance)
