from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude out of range")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude out of range")


@dataclass(frozen=True, slots=True)
class Polygon:
    """Closed ring of [lat, lng] vertices. Ray-casting point-in-polygon."""

    vertices: tuple[GeoPoint, ...]

    def __post_init__(self) -> None:
        if len(self.vertices) < 3:
            raise ValueError("polygon needs at least 3 vertices")

    def contains(self, point: GeoPoint) -> bool:
        inside = False
        vertices = self.vertices
        j = len(vertices) - 1
        for i, vertex in enumerate(vertices):
            xi, yi = vertex.longitude, vertex.latitude
            xj, yj = vertices[j].longitude, vertices[j].latitude
            intersects = ((yi > point.latitude) != (yj > point.latitude)) and (
                point.longitude < (xj - xi) * (point.latitude - yi) / (yj - yi + 1e-16) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside
