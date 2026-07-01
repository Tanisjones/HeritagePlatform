"""
Pluggable walking-route provider.

Mirrors the AI provider abstraction in ``apps.ai_services.providers``: a
``RouteProvider`` protocol, concrete providers, and a settings-driven factory.
Env-gated and OFF by default (``ROUTING_PROVIDER=straight_line``) so production
is unaffected until an OSRM server is configured.
"""
from __future__ import annotations

from typing import Iterable, Optional

from django.conf import settings

from .base import Coord, RouteProvider, RouteResult, RouteStep
from .straight_line import StraightLineProvider, haversine_m, path_length_m


def get_route_provider() -> RouteProvider:
    """Return the configured routing provider (straight-line unless OSRM is set)."""
    provider = getattr(settings, "ROUTING_PROVIDER", "straight_line")
    if provider == "osrm" and getattr(settings, "OSRM_URL", ""):
        from .osrm import OsrmProvider

        return OsrmProvider()
    return StraightLineProvider()


def _stop_coords(stops: Iterable) -> list[Coord]:
    """Extract ``(lng, lat)`` from each stop's heritage item location, in order."""
    coords: list[Coord] = []
    for stop in stops:
        location = getattr(getattr(stop, "heritage_item", None), "location", None)
        if location is None:
            continue
        # GEOS point: ``.x`` is lng, ``.y`` is lat.
        lng, lat = getattr(location, "x", None), getattr(location, "y", None)
        if lng is None or lat is None:
            continue
        coords.append((float(lng), float(lat)))
    return coords


def build_path_for_stops(stops: Iterable) -> Optional[RouteResult]:
    """
    Route through an ordered iterable of ``RouteStop`` instances.

    Tries the configured provider first; if it yields nothing (OSRM down /
    unconfigured / too few points) falls back to the straight-line provider, so
    a configured-but-unreachable OSRM still produces a usable path instead of an
    error. Returns ``None`` only when there are fewer than two locatable stops.
    """
    coords = _stop_coords(stops)
    if len(coords) < 2:
        return None

    result = get_route_provider().route(coords)
    if result is None:
        result = StraightLineProvider().route(coords)
    return result


__all__ = [
    "RouteProvider",
    "RouteResult",
    "RouteStep",
    "Coord",
    "StraightLineProvider",
    "get_route_provider",
    "build_path_for_stops",
    "haversine_m",
    "path_length_m",
]
