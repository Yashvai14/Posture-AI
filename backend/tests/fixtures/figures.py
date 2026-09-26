"""Procedurally drawn human figures with known geometry.

They are simple enough to be license-free test inputs, yet realistic enough for MediaPipe to detect, which
lets tests exercise the real pose model end to end.
"""

import math

from PIL import Image, ImageDraw, ImageFilter

SKIN = (224, 182, 150)
SHIRT = (60, 90, 150)
PANTS = (50, 50, 60)
SHOE = (30, 30, 30)
HAIR = (60, 40, 30)
BACKGROUND = (232, 232, 228)


def _limb(draw: ImageDraw.ImageDraw, a: tuple[float, float], b: tuple[float, float], width: float, fill) -> None:
    """A capsule from a to b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    draw.polygon(
        [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], fill=fill
    )
    r = width / 2
    for p in (a, b):
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)


def front_figure(shoulder_tilt_deg: float = 0.0, width: int = 600, height: int = 1000) -> Image.Image:
    """Front view. Positive tilt raises the figure's left shoulder (image right)."""
    im = Image.new("RGB", (width, height), BACKGROUND)
    d = ImageDraw.Draw(im)
    cx = width / 2
    half = 110
    rise = half * math.tan(math.radians(shoulder_tilt_deg))
    right_sh = (cx - half, 235 + rise)  # figure's right shoulder, image left
    left_sh = (cx + half, 235 - rise)
    # legs
    _limb(d, (cx - 50, 560), (cx - 55, 900), 80, PANTS)
    _limb(d, (cx + 50, 560), (cx + 55, 900), 80, PANTS)
    d.rounded_rectangle([cx - 110, 905, cx - 5, 950], 15, fill=SHOE)
    d.rounded_rectangle([cx + 5, 905, cx + 110, 950], 15, fill=SHOE)
    d.rounded_rectangle([cx - 100, 500, cx + 100, 580], 12, fill=PANTS)
    # torso and arms
    d.polygon([right_sh, left_sh, (cx + 100, 520), (cx - 100, 520)], fill=SHIRT)
    _limb(d, right_sh, (right_sh[0] - 25, right_sh[1] + 260), 55, SHIRT)
    _limb(d, left_sh, (left_sh[0] + 25, left_sh[1] + 260), 55, SHIRT)
    d.ellipse([right_sh[0] - 55, right_sh[1] + 250, right_sh[0] + 5, right_sh[1] + 310], fill=SKIN)
    d.ellipse([left_sh[0] - 5, left_sh[1] + 250, left_sh[0] + 55, left_sh[1] + 310], fill=SKIN)
    # neck and head
    d.rectangle([cx - 22, 185, cx + 22, 235], fill=SKIN)
    d.ellipse([cx - 60, 40, cx + 60, 190], fill=SKIN)
    d.chord([cx - 62, 30, cx + 62, 130], 180, 360, fill=HAIR)
    for ex in (cx - 23, cx + 23):
        d.ellipse([ex - 9, 100, ex + 9, 112], fill=(255, 255, 255))
        d.ellipse([ex - 4, 102, ex + 4, 110], fill=(40, 30, 20))
    d.polygon([(cx, 115), (cx - 8, 140), (cx + 8, 140)], fill=(200, 150, 120))
    d.arc([cx - 25, 145, cx + 25, 170], 20, 160, fill=(150, 60, 60), width=4)
    d.ellipse([cx - 72, 95, cx - 55, 135], fill=SKIN)
    d.ellipse([cx + 55, 95, cx + 72, 135], fill=SKIN)
    return im.filter(ImageFilter.GaussianBlur(1.2))


def side_figure(head_forward_px: float = 0.0, width: int = 600, height: int = 1000) -> Image.Image:
    """Right-facing side view. `head_forward_px` moves the head and neck forward of the shoulder."""
    im = Image.new("RGB", (width, height), BACKGROUND)
    d = ImageDraw.Draw(im)
    cx = width / 2
    shoulder = (cx, 250)
    hip = (cx, 540)
    head_c = (cx + 15 + head_forward_px, 120)
    # legs: far leg set back and darker, near leg in front; feet point forward with a visible heel
    for offset, colour, shoe in ((-38, (38, 38, 48), (20, 20, 20)), (0, PANTS, SHOE)):
        knee = (cx + offset + 6, 720)
        ankle = (cx + offset, 880)
        _limb(d, (hip[0] + offset, hip[1]), knee, 78, colour)
        _limb(d, knee, ankle, 62, colour)
        _limb(d, (ankle[0] + 6, ankle[1] + 12), (ankle[0] - 6, ankle[1] + 30), 34, SKIN)
        d.polygon(
            [
                (ankle[0] - 32, ankle[1] + 22),
                (ankle[0] + 70, ankle[1] + 40),
                (ankle[0] + 78, ankle[1] + 62),
                (ankle[0] - 36, ankle[1] + 62),
            ],
            fill=shoe,
        )
    # torso
    d.rounded_rectangle([cx - 60, 225, cx + 55, 580], 40, fill=SHIRT)
    # neck
    _limb(d, (shoulder[0] + 5, shoulder[1] - 20), (head_c[0] - 5, head_c[1] + 50), 48, SKIN)
    # arm
    _limb(d, (shoulder[0], shoulder[1] + 5), (cx + 10, 500), 50, (70, 100, 165))
    d.ellipse([cx - 18, 490, cx + 38, 546], fill=SKIN)
    # head in profile
    hx, hy = head_c
    d.ellipse([hx - 62, hy - 75, hx + 58, hy + 75], fill=SKIN)
    d.chord([hx - 66, hy - 82, hx + 60, hy + 20], 180, 360, fill=HAIR)
    d.pieslice([hx - 70, hy - 82, hx + 20, hy + 30], 150, 270, fill=HAIR)
    d.polygon([(hx + 55, hy - 10), (hx + 78, hy + 18), (hx + 55, hy + 24)], fill=(214, 170, 140))
    d.ellipse([hx + 22, hy - 16, hx + 38, hy - 4], fill=(255, 255, 255))
    d.ellipse([hx + 28, hy - 14, hx + 36, hy - 6], fill=(40, 30, 20))
    d.arc([hx + 25, hy + 32, hx + 50, hy + 50], 20, 120, fill=(150, 60, 60), width=4)
    d.ellipse([hx - 18, hy - 8, hx + 4, hy + 26], fill=(205, 160, 130))
    return im.filter(ImageFilter.GaussianBlur(1.2))
