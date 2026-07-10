"""
Role & per-city governance helpers — the single source of truth.

Platform-wide capabilities (tourist / contributor / teacher) live on
``UserProfile.role``. Per-city governance (curator / moderator) lives in
``cities.CityRole``; staff/superusers are global. A profile role slug of
'curator'/'moderator' grants nothing by itself since the multi-city refactor.

Scope rule: curator-as-GATEKEEPER (moderation queue, approve/reject, route
governance) is strictly per-city — a Riobamba curator cannot act on another
city's content. Curator-as-authoring-helper on education/LOM surfaces is
any-city (those surfaces are teacher-driven, and teachers are global).
"""

from rest_framework import permissions

from apps.cities.models import CityRole
from apps.cities.request import get_request_city


def get_role_slug(user):
    """The user's platform-wide profile role slug, or None."""
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", None)
    return getattr(role, "slug", None)


def user_city_ids(user, role):
    """IDs of cities where `user` holds `role` — cached on the user object
    so repeated permission checks + queryset scoping cost one query."""
    if not user or not user.is_authenticated:
        return set()
    cache = getattr(user, "_hp_city_role_ids", None)
    if cache is None:
        cache = {}
        user._hp_city_role_ids = cache
    if role not in cache:
        cache[role] = set(
            CityRole.objects.filter(user=user, role=role).values_list("city_id", flat=True)
        )
    return cache[role]


def is_city_curator(user, city_or_id):
    """Curator of this specific city (staff are curators everywhere)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    city_id = getattr(city_or_id, "id", city_or_id)
    if city_id is None:
        return False
    return city_id in user_city_ids(user, CityRole.ROLE_CURATOR)


def is_curator_anywhere(user):
    """Curator of at least one city (menu gating / any-city authoring help)."""
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user_city_ids(user, CityRole.ROLE_CURATOR))
    )


class IsCurator(permissions.BasePermission):
    """
    City-aware curator gate.

    View level: staff pass; when an action browses a collection, a request city
    (?city=/X-City) means the user must be THAT city's curator; otherwise any
    curator assignment suffices (those endpoints are additionally queryset-scoped
    to assigned cities). Actions that name their own targets — every detail
    action, plus collection actions like `bulk` that take explicit ids — defer to
    the target's city instead: the active city travels on every request and says
    nothing about which item is open, so gating on it would reject a cross-city
    item the curator legitimately governs.
    Object level: the object's own city decides.
    """

    #: Collection actions that address explicit targets rather than browsing the
    #: request city's collection. Their querysets confine targets to governed cities.
    TARGETED_COLLECTION_ACTIONS = frozenset({'bulk'})

    def _targets_own_objects(self, view):
        if getattr(view, 'detail', False):
            return True
        return getattr(view, 'action', None) in self.TARGETED_COLLECTION_ACTIONS

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        city = get_request_city(request)
        if city is not None and not self._targets_own_objects(view):
            return is_city_curator(user, city)
        return is_curator_anywhere(user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        city_id = getattr(obj, "city_id", None)
        if city_id is not None:
            return is_city_curator(user, city_id)
        return self.has_permission(request, view)


class IsTeacher(permissions.BasePermission):
    """
    Teacher access: users with role slug 'teacher' (or staff). Deliberately
    GLOBAL — teaching is a capability, not a per-city governance power.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and (user.is_staff or get_role_slug(user) == "teacher")
        )


class IsContributor(permissions.BasePermission):
    """Contributor access: authenticated users."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)


class IsOwnerOrCurator(permissions.BasePermission):
    """
    Object access: owner (contributor), the object's city curator, or staff.
    Objects without a `city` fall back to the any-city curator check.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        city_id = getattr(obj, "city_id", None)
        if city_id is not None:
            if is_city_curator(user, city_id):
                return True
        elif is_curator_anywhere(user):
            return True
        return getattr(obj, "contributor_id", None) == user.id
