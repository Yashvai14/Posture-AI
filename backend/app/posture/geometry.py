"""Plane geometry in image coordinates (x to the right, y downwards, units in pixels)."""

import math

Point = tuple[float, float]


def midpoint(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def angle_from_vertical(top: Point, bottom: Point) -> float:
    """Signed angle in degrees between the upward vertical at `bottom` and the segment bottom→top.

    0 means `top` is directly above `bottom`; positive means `top` lies to the right (+x) of it.
    """
    dx = top[0] - bottom[0]
    dy = bottom[1] - top[1]
    return math.degrees(math.atan2(dx, dy))


def tilt_from_horizontal(a: Point, b: Point) -> float:
    """Signed angle in degrees of the line through a and b relative to horizontal, in (-90, 90].

    Positive means the point further right in the image is higher.
    """
    left, right = sorted((a, b), key=lambda p: p[0])
    dx = right[0] - left[0]
    dy = left[1] - right[1]
    if dx == 0:
        return 90.0
    return math.degrees(math.atan(dy / dx))


def interior_angle(a: Point, vertex: Point, c: Point) -> float:
    """Angle a-vertex-c in degrees, in [0, 180]."""
    v1 = (a[0] - vertex[0], a[1] - vertex[1])
    v2 = (c[0] - vertex[0], c[1] - vertex[1])
    norm = math.hypot(*v1) * math.hypot(*v2)
    if norm == 0:
        raise ValueError("degenerate angle: coincident points")
    cos_angle = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / norm))
    return math.degrees(math.acos(cos_angle))


def horizontal_offset_from_line(p: Point, a: Point, b: Point) -> float:
    """Horizontal offset (pixels) of p from the line through a and b, measured at p's height.

    Positive means p lies to the right of the line.
    """
    if a[1] == b[1]:
        raise ValueError("line is horizontal")
    t = (p[1] - a[1]) / (b[1] - a[1])
    x_on_line = a[0] + t * (b[0] - a[0])
    return p[0] - x_on_line
