from rest_framework import permissions


def _get_role_slug(user):
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", None)
    return getattr(role, "slug", None)


class IsCurator(permissions.BasePermission):
    """
    Curator access: staff users or users with role slug 'curator'.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or _get_role_slug(user) == "curator"))


class IsTeacher(permissions.BasePermission):
    """
    Teacher access: users with role slug 'teacher' (or staff).
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or _get_role_slug(user) == "teacher"))


class IsContributor(permissions.BasePermission):
    """
    Contributor access: authenticated users.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)


class IsOwnerOrCurator(permissions.BasePermission):
    """
    Object access: owner (contributor) or curator.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or _get_role_slug(user) == "curator":
            return True
        return getattr(obj, "contributor_id", None) == user.id

