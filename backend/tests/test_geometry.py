import pytest

from app.posture.geometry import (
    angle_from_vertical,
    horizontal_offset_from_line,
    interior_angle,
    midpoint,
    tilt_from_horizontal,
)


def test_angle_from_vertical_sign_and_magnitude():
    assert angle_from_vertical((0, -10), (0, 0)) == pytest.approx(0)
    assert angle_from_vertical((10, -10), (0, 0)) == pytest.approx(45)
    assert angle_from_vertical((-10, -10), (0, 0)) == pytest.approx(-45)
    assert angle_from_vertical((10, 0), (0, 0)) == pytest.approx(90)


def test_tilt_from_horizontal_is_order_independent():
    assert tilt_from_horizontal((0, 0), (100, 0)) == pytest.approx(0)
    # Right point higher (smaller y) → positive.
    assert tilt_from_horizontal((0, 0), (100, -100)) == pytest.approx(45)
    assert tilt_from_horizontal((100, -100), (0, 0)) == pytest.approx(45)
    assert tilt_from_horizontal((0, 0), (100, 10)) < 0
    assert tilt_from_horizontal((5, 0), (5, 50)) == 90


def test_interior_angle():
    assert interior_angle((0, -10), (0, 0), (0, 10)) == pytest.approx(180)
    assert interior_angle((10, 0), (0, 0), (0, 10)) == pytest.approx(90)
    with pytest.raises(ValueError):
        interior_angle((0, 0), (0, 0), (1, 1))


def test_horizontal_offset_from_line():
    # Vertical line x = 10; a point at x = 13 is 3 px to the right.
    assert horizontal_offset_from_line((13, 5), (10, 0), (10, 20)) == pytest.approx(3)
    # Slanted line through (0,0) and (10,10): at y = 5 the line is at x = 5.
    assert horizontal_offset_from_line((2, 5), (0, 0), (10, 10)) == pytest.approx(-3)
    with pytest.raises(ValueError):
        horizontal_offset_from_line((0, 0), (0, 5), (10, 5))


def test_midpoint():
    assert midpoint((0, 0), (10, 20)) == (5, 10)
