from __future__ import annotations

import math
from typing import Optional

from django.conf import settings

from .base import Coord, RouteProvider, RouteResult

_EARTH_RADIUS_M = 6_371_000.0

# Default average walking speed (m/s) ≈ 4.7 km/h. Overridable via settings so
# the estimate can be tuned without a code change.
_DEFAULT_WALKING_SPEED_MPS = 1.3


def haversine_m(a: Coord, b: Coord) -> float:
    """Great-circle distance in metres between two ``(lng, lat)`` points."""
    lng1, lat1 = a
    lng2, lat2 = b
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    h = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def path_length_m(coords: list[Coord]) -> float:
    """Total great-circle length of a polyline through ``coords``."""
    return sum(haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


class StraightLineProvider(RouteProvider):
    """
    Fallback provider needing no external service: connects the stops with
    straight segments and estimates distance/duration geometrically. Used when
    no routing engine is configured, or when the configured engine is
    unreachable (see ``build_path_for_stops``).
    """

    def route(self, coords: list[Coord]) -> Optional[RouteResult]:
        if len(coords) < 2:
            return None
        distance_m = path_length_m(coords)
        speed = float(getattr(settings, "ROUTING_WALKING_SPEED_MPS", _DEFAULT_WALKING_SPEED_MPS))
        duration_s = distance_m / speed if speed > 0 else 0.0
        return RouteResult(
            geometry={"type": "LineString", "coordinates": [list(c) for c in coords]},
            distance_m=distance_m,
            duration_s=duration_s,
            provider="straight_line",
            steps=[],
        )


__all__ = ["StraightLineProvider", "haversine_m", "path_length_m"]
