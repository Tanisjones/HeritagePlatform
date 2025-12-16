from django.apps import apps
from django.db.models import F

from .models import PointTransaction, UserBadge, Badge, Level


POINT_RULES = {
    "register": {"points": 10, "reason": "Register account", "unique_reason": True},
    "profile_complete": {"points": 20, "reason": "Profile completed", "unique_reason": True},
    "first_contribution": {"points": 50, "reason": "First contribution", "unique_reason": True},
    "contribution_approved": {"points": 25, "reason": "Contribution approved", "unique_reference": True},
    "high_quality_bonus": {"points": 15, "reason": "High-quality contribution bonus", "unique_reference": True},
    "annotation_added": {"points": 5, "reason": "Annotation added", "unique_reference": True},
    "route_completed": {"points": 30, "reason": "Route completed", "unique_reference": True},
    "first_route_category": {"points": 20, "reason": "First route in category", "unique_reason": True},
    "moderation_review": {"points": 10, "reason": "Contribution reviewed", "unique_reference": True},
}


def _get_user_profile(user):
    """
    Safely get or create the user's profile.
    """
    UserProfile = apps.get_model("users", "UserProfile")
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _transaction_exists(user, reason, reference_object=None):
    filters = {"user": user, "reason": reason}
    if reference_object:
        filters.update(
            {
                "reference_type": reference_object.__class__.__name__,
                "reference_id": str(getattr(reference_object, "id", "")),
            }
        )
    return PointTransaction.objects.filter(**filters).exists()


def add_points(user, points: int, reason: str, reference_object=None, unique_reason=False, unique_reference=False):
    """
    Adds points to a user, logs a transaction, and updates the user's level.
    """
    if not user:
        return None

    profile = _get_user_profile(user)

    if unique_reference and reference_object and _transaction_exists(user, reason, reference_object):
        return None

    if unique_reason and _transaction_exists(user, reason):
        return None

    transaction = PointTransaction.objects.create(
        user=user,
        points=points,
        reason=reason,
        reference_type=reference_object.__class__.__name__ if reference_object else "",
        reference_id=str(reference_object.id) if reference_object else "",
    )

    # Atomic points update to avoid race conditions
    profile.points = F("points") + points
    profile.save(update_fields=["points"])
    profile.refresh_from_db(fields=["points"])
    sync_user_level(user, profile)
    return transaction


def get_level_for_points(points: int):
    """
    Returns the Level object that matches the user's current points.
    """
    return (
        Level.objects.filter(min_points__lte=points, max_points__gte=points)
        .order_by("-min_points")
        .first()
        or Level.objects.filter(min_points__lte=points).order_by("-min_points").first()
    )


def sync_user_level(user, profile=None):
    """
    Align the user's numeric level with the configured Level ranges.
    """
    profile = profile or _get_user_profile(user)
    level_obj = get_level_for_points(profile.points)
    target_level = level_obj.number if level_obj else max(profile.level or 1, 1)

    if profile.level != target_level:
        profile.level = target_level
        profile.save(update_fields=["level"])
    return profile.level


def award_badge(user, badge: Badge):
    """
    Awards a badge to a user and applies its point value.
    """
    if not user or not badge:
        return None

    if UserBadge.objects.filter(user=user, badge=badge).exists():
        return None

    user_badge = UserBadge.objects.create(user=user, badge=badge)

    if badge.points_value:
        add_points(
            user,
            badge.points_value,
            f"Awarded badge: {badge.name}",
            reference_object=badge,
            unique_reference=True,
        )

    return user_badge


def award_badge_by_name(user, badge_name: str):
    """
    Helper to fetch and award a badge by its name.
    """
    badge = Badge.objects.filter(name=badge_name).first()
    if badge:
        return award_badge(user, badge)
    return None


def handle_registration(user):
    """
    Apply gamification rewards for a new registration.
    """
    rule = POINT_RULES["register"]
    add_points(user, rule["points"], rule["reason"], unique_reason=rule["unique_reason"])
    sync_user_level(user)


def is_profile_complete(profile):
    """
    Determine if a profile meets the completion criteria.
    """
    return bool(profile.display_name and profile.bio)


def handle_profile_completion(profile):
    """
    Reward users for completing their profile (one-time).
    """
    if not is_profile_complete(profile):
        return None
    rule = POINT_RULES["profile_complete"]
    return add_points(profile.user, rule["points"], rule["reason"], unique_reason=rule["unique_reason"])


def handle_contribution_created(contribution):
    """
    Reward the contributor for their first submission.
    """
    contributor = getattr(contribution, "contributor", None)
    if not contributor:
        return None

    rule = POINT_RULES["first_contribution"]
    return add_points(
        contributor,
        rule["points"],
        rule["reason"],
        reference_object=contribution,
        unique_reason=rule["unique_reason"],
    )


def is_high_quality_contribution(contribution):
    """
    Heuristic to determine if a contribution is high quality.
    """
    description = getattr(contribution, "description", "") or ""
    has_media = (
        hasattr(contribution, "images")
        and (contribution.images.exists() or contribution.audio.exists() or contribution.video.exists())
    )
    has_location = bool(getattr(contribution, "address", "") or getattr(contribution, "parish_id", None))
    return len(description) >= 250 and has_media and has_location


def handle_contribution_approved(contribution, moderator=None):
    """
    Reward contributor (and moderator) when a contribution is approved.
    """
    contributor = getattr(contribution, "contributor", None)
    rule = POINT_RULES["contribution_approved"]

    if contributor:
        add_points(
            contributor,
            rule["points"],
            rule["reason"],
            reference_object=contribution,
            unique_reference=rule["unique_reference"],
        )

        if is_high_quality_contribution(contribution):
            bonus_rule = POINT_RULES["high_quality_bonus"]
            add_points(
                contributor,
                bonus_rule["points"],
                bonus_rule["reason"],
                reference_object=contribution,
                unique_reference=bonus_rule["unique_reference"],
            )

        evaluate_contribution_badges(contributor)

    if moderator and moderator != contributor:
        reward_moderation_review(moderator, contribution)


def reward_moderation_review(moderator, contribution):
    """
    Reward moderators for reviewing contributions.
    """
    rule = POINT_RULES["moderation_review"]
    add_points(
        moderator,
        rule["points"],
        rule["reason"],
        reference_object=contribution,
        unique_reference=rule["unique_reference"],
    )


def handle_annotation_created(annotation):
    """
    Reward annotations and check related badges.
    """
    user = getattr(annotation, "user", None)
    if not user:
        return None

    rule = POINT_RULES["annotation_added"]
    add_points(
        user,
        rule["points"],
        rule["reason"],
        reference_object=annotation,
        unique_reference=rule["unique_reference"],
    )
    evaluate_annotation_badges(user)


def handle_route_completed(route_progress):
    """
    Reward a user for completing a route and check route badges.
    """
    user = getattr(route_progress, "user", None)
    if not user or not getattr(route_progress, "completed_at", None):
        return None

    route = getattr(route_progress, "route", None)
    rule = POINT_RULES["route_completed"]
    add_points(
        user,
        rule["points"],
        rule["reason"],
        reference_object=route_progress,
        unique_reference=rule["unique_reference"],
    )

    if route and getattr(route, "theme", None):
        category_rule = POINT_RULES["first_route_category"]
        themed_reason = f"{category_rule['reason']}: {route.theme}"
        add_points(
            user,
            category_rule["points"],
            themed_reason,
            unique_reason=category_rule.get("unique_reason", False),
        )

    evaluate_route_badges(user)


def evaluate_contribution_badges(user):
    """
    Evaluate and award contribution-related badges.
    """
    contribution_count = user.contributed_heritage.count()
    if contribution_count >= 1:
        award_badge_by_name(user, "Primer Aporte")
    if contribution_count >= 10:
        award_badge_by_name(user, "Prolífico")
    if contribution_count >= 50:
        award_badge_by_name(user, "Experto Local")


def evaluate_annotation_badges(user):
    """
    Evaluate and award annotation-related badges.
    """
    annotation_count = user.annotations.count()
    if annotation_count >= 10:
        award_badge_by_name(user, "Colaborador")


def evaluate_route_badges(user):
    """
    Evaluate and award route-related badges.
    """
    UserRouteProgress = apps.get_model("routes", "UserRouteProgress")
    completed = UserRouteProgress.objects.filter(user=user, completed_at__isnull=False).count()
    if completed >= 5:
        award_badge_by_name(user, "Caminante")
    if completed >= 20:
        award_badge_by_name(user, "Peregrino")
