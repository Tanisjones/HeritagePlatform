"""
Re-export shim: role/permission logic is consolidated in
apps.users.permissions (city-aware since the multi-city refactor).
Existing importers of this module keep working unchanged.
"""

from apps.users.permissions import (  # noqa: F401
    IsContributor,
    IsCurator,
    IsOwnerOrCurator,
    IsTeacher,
    get_role_slug,
)

# Legacy private alias (pre-refactor name used by a few importers).
_get_role_slug = get_role_slug
