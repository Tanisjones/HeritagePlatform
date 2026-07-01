from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from django.conf import settings

from .base import Coord, RouteProvider, RouteResult, RouteStep

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 8


class OsrmProvider(RouteProvider):
    """
    Routes via an OSRM server's ``/route`` service (foot profile), returning a
    street-snapped GeoJSON path plus turn-by-turn steps and a real ETA.

    ``OSRM_URL`` is read from settings (e.g. ``http://osrm:5000``). Every failure
    mode — network error, HTTP >= 400, ``code != "Ok"``, malformed body — returns
    ``None`` instead of raising, so a misconfigured or down OSRM degrades to the
    straight-line fallback rather than breaking a route save.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or getattr(settings, "OSRM_URL", "")).rstrip("/")

    def route(self, coords: list[Coord]) -> Optional[RouteResult]:
        if not self._base_url or len(coords) < 2:
            return None

        # OSRM expects ``lng,lat;lng,lat;...`` in path-order.
        coord_str = ";".join(f"{lng},{lat}" for lng, lat in coords)
        url = f"{self._base_url}/route/v1/foot/{coord_str}"
        timeout = float(getattr(settings, "ROUTING_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS))

        try:
            resp = httpx.get(
                url,
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "true",
                },
                timeout=httpx.Timeout(timeout),
            )
        except httpx.RequestError as exc:
            logger.warning("OSRM request failed: %s", exc)
            return None

        if resp.status_code >= 400:
            logger.warning("OSRM error: HTTP %s", resp.status_code)
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.warning("OSRM returned non-JSON response")
            return None

        return _parse_osrm(data)


def _parse_osrm(data: Any) -> Optional[RouteResult]:
    if not isinstance(data, dict) or data.get("code") != "Ok":
        return None
    routes = data.get("routes")
    if not isinstance(routes, list) or not routes:
        return None
    route = routes[0]
    geometry = route.get("geometry")
    if not (isinstance(geometry, dict) and geometry.get("type") == "LineString"):
        return None
    # Reject a structurally-valid-but-degenerate result (empty/1-point geometry
    # or zero distance) so callers fall back to the straight-line provider rather
    # than persisting an empty path / 0 km route.
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    distance_m = float(route.get("distance") or 0.0)
    if distance_m <= 0:
        return None

    steps: list[RouteStep] = []
    for leg in route.get("legs", []) or []:
        for step in (leg.get("steps", []) if isinstance(leg, dict) else []) or []:
            if not isinstance(step, dict):
                continue
            maneuver = step.get("maneuver") or {}
            instruction = maneuver.get("type") or ""
            modifier = maneuver.get("modifier")
            if modifier:
                instruction = f"{instruction} {modifier}".strip()
            steps.append(
                RouteStep(
                    instruction=instruction or step.get("name", ""),
                    distance_m=float(step.get("distance") or 0.0),
                    duration_s=float(step.get("duration") or 0.0),
                    name=step.get("name", "") or "",
                )
            )

    return RouteResult(
        geometry=geometry,
        distance_m=distance_m,
        duration_s=float(route.get("duration") or 0.0),
        provider="osrm",
        steps=steps,
    )


__all__ = ["OsrmProvider"]
