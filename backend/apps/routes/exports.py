"""
GPX and KML exporters for heritage routes.

Built with the stdlib ``xml.etree.ElementTree`` (same approach as the education
SCORM/LOM XML builders — no lxml dependency). Waypoints/placemarks come from the
ordered stops; the track/line uses the route ``path`` LineString, falling back to
straight segments between stops when no path has been generated.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional
from xml.etree import ElementTree as ET

GPX_CONTENT_TYPE = "application/gpx+xml"
KML_CONTENT_TYPE = "application/vnd.google-earth.kml+xml"

_GPX_NS = "http://www.topografix.com/GPX/1/1"
_KML_NS = "http://www.opengis.net/kml/2.2"


def slugify_filename(value: str, fallback: str = "route") -> str:
    """Filesystem-safe slug for a download filename (mirrors scorm.py)."""
    value = (value or "").strip()
    if not value:
        return fallback
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-.")
    return value or fallback


def _pretty_xml(elem: ET.Element) -> str:
    try:
        ET.indent(elem, space="  ")
    except Exception:
        pass
    return ET.tostring(elem, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _stop_lng_lat(stop) -> Optional[tuple[float, float]]:
    """``(lng, lat)`` of a stop's heritage item, or None if unlocatable."""
    location = getattr(getattr(stop, "heritage_item", None), "location", None)
    if location is None:
        return None
    lng, lat = getattr(location, "x", None), getattr(location, "y", None)
    if lng is None or lat is None:
        return None
    return float(lng), float(lat)


def _path_coords(route) -> list[tuple[float, float]]:
    """``(lng, lat)`` vertices of the route path, else the stop coordinates."""
    path = getattr(route, "path", None)
    if path is not None:
        try:
            coords = [(float(lng), float(lat)) for lng, lat in path.coords]
            if coords:
                return coords
        except (TypeError, ValueError):
            pass
    ordered = _ordered_stops(route)
    return [c for c in (_stop_lng_lat(s) for s in ordered) if c is not None]


def _ordered_stops(route) -> Iterable:
    stops = getattr(route, "stops", None)
    if stops is None:
        return []
    # Works for both a related manager and a plain list of stops.
    try:
        return stops.all().order_by("order")
    except AttributeError:
        return sorted(stops, key=lambda s: getattr(s, "order", 0))


def build_gpx(route) -> str:
    """Serialize a route to a GPX 1.1 document (waypoints per stop + a track)."""
    gpx = ET.Element("gpx", {
        "version": "1.1",
        "creator": "HeritagePlatform",
        "xmlns": _GPX_NS,
    })

    metadata = ET.SubElement(gpx, "metadata")
    ET.SubElement(metadata, "name").text = route.title or ""
    if getattr(route, "description", ""):
        ET.SubElement(metadata, "desc").text = route.description

    for stop in _ordered_stops(route):
        coord = _stop_lng_lat(stop)
        if coord is None:
            continue
        lng, lat = coord
        wpt = ET.SubElement(gpx, "wpt", {"lat": f"{lat}", "lon": f"{lng}"})
        ET.SubElement(wpt, "name").text = getattr(stop.heritage_item, "title", "") or ""
        if getattr(stop, "arrival_instructions", ""):
            ET.SubElement(wpt, "desc").text = stop.arrival_instructions

    coords = _path_coords(route)
    if len(coords) >= 2:
        trk = ET.SubElement(gpx, "trk")
        ET.SubElement(trk, "name").text = route.title or ""
        trkseg = ET.SubElement(trk, "trkseg")
        for lng, lat in coords:
            ET.SubElement(trkseg, "trkpt", {"lat": f"{lat}", "lon": f"{lng}"})

    return _pretty_xml(gpx)


def build_kml(route) -> str:
    """Serialize a route to a KML 2.2 document (placemarks + a line)."""
    kml = ET.Element("kml", {"xmlns": _KML_NS})
    doc = ET.SubElement(kml, "Document")
    ET.SubElement(doc, "name").text = route.title or ""
    if getattr(route, "description", ""):
        ET.SubElement(doc, "description").text = route.description

    for stop in _ordered_stops(route):
        coord = _stop_lng_lat(stop)
        if coord is None:
            continue
        lng, lat = coord
        placemark = ET.SubElement(doc, "Placemark")
        ET.SubElement(placemark, "name").text = getattr(stop.heritage_item, "title", "") or ""
        if getattr(stop, "arrival_instructions", ""):
            ET.SubElement(placemark, "description").text = stop.arrival_instructions
        point = ET.SubElement(placemark, "Point")
        ET.SubElement(point, "coordinates").text = f"{lng},{lat},0"

    coords = _path_coords(route)
    if len(coords) >= 2:
        placemark = ET.SubElement(doc, "Placemark")
        ET.SubElement(placemark, "name").text = route.title or ""
        line = ET.SubElement(placemark, "LineString")
        ET.SubElement(line, "tessellate").text = "1"
        ET.SubElement(line, "coordinates").text = " ".join(f"{lng},{lat},0" for lng, lat in coords)

    return _pretty_xml(kml)


__all__ = [
    "build_gpx",
    "build_kml",
    "slugify_filename",
    "GPX_CONTENT_TYPE",
    "KML_CONTENT_TYPE",
]
