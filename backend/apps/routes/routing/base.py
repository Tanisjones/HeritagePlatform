from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class RouteStep:
    """A single turn-by-turn navigation instruction."""

    instruction: str
    distance_m: float
    duration_s: float
    name: str = ""


@dataclass(frozen=True)
class RouteResult:
    """
    The outcome of routing an ordered list of stop coordinates.

    ``geometry`` is a GeoJSON ``LineString`` dict (``coordinates`` are
    ``[lng, lat]`` pairs, matching the GeoJSON / PostGIS axis order).
    """

    geometry: dict
    distance_m: float
    duration_s: float
    provider: str
    steps: list[RouteStep] = field(default_factory=list)


# A coordinate is an ``(lng, lat)`` pair (GeoJSON axis order).
Coord = tuple[float, float]


@runtime_checkable
class RouteProvider(Protocol):
    """
    Turns an ordered list of ``(lng, lat)`` coordinates into a walkable route.

    Implementations MUST NOT raise on an unreachable/unconfigured backend —
    they return ``None`` so callers can fall back gracefully (a routing failure
    must never break saving a route). Mirrors the ``ChatProvider`` protocol in
    ``apps.ai_services.providers.base``.
    """

    def route(self, coords: list[Coord]) -> Optional[RouteResult]:
        ...


__all__ = ["RouteStep", "RouteResult", "RouteProvider", "Coord"]
