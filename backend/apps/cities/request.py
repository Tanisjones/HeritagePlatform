"""
Per-request city resolution.

Contract (mirrored by the SPA): the `?city=<slug>` query param wins over the
`X-City` header. Absence of both — or an unknown/inactive slug — resolves to
None, which read endpoints treat as "unfiltered" (backwards compatible) and
write endpoints replace with `City.get_default()`.
"""

from .models import City


def get_request_city(request):
    """Resolve the active City for this request, memoized on the request."""
    if request is None:
        return None
    if hasattr(request, '_hp_city'):
        return request._hp_city

    params = getattr(request, 'query_params', None)
    if params is None:
        params = request.GET
    slug = params.get('city') or request.headers.get('X-City')

    city = None
    if slug:
        city = City.objects.filter(slug=slug, is_active=True).first()

    request._hp_city = city
    return city


def get_request_city_or_default(request):
    """Write-path resolution: request city, else the platform default city."""
    return get_request_city(request) or City.get_default()
