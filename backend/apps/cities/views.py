from rest_framework import permissions, viewsets

from .models import City
from .serializers import CitySerializer


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public catalog of active cities on the platform.

    The SPA loads this on boot to populate the city switcher; content
    endpoints are scoped per request via `?city=<slug>` or the `X-City`
    header (see apps.cities.request.get_request_city).
    """
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    pagination_class = None
