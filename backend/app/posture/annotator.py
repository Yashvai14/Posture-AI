"""Draws the detected skeleton, reference lines and measured angles onto the photo.

Only draws landmarks and measurement overlays that are actually visible in the frame.
"""

import math
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.posture.classifier import Severity
from app.posture.geometry import midpoint
from app.posture.landmarks import LM, SKELETON, side_landmarks
from app.posture.pipeline import PostureResult
from app.posture.quality import near_side

FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "DejaVuSans-Bold.ttf"

SKELETON_COLOR = (13, 110, 253, 230)
JOINT_FILL = (255, 255, 255, 255)
REFERENCE_COLOR = (100, 116, 139, 220)
SEVERITY_COLORS = {
    None: (16, 185, 129, 255),
    Severity.MILD: (217, 119, 6, 255),
    Severity.MODERATE: (234, 88, 12, 255),
    Severity.PRONOUNCED: (220, 38, 38, 255),
}
MIN_DRAW_CONFIDENCE = 0.3

Point = tuple[float, float]


class _Canvas:
    def __init__(self, image: Image.Image):
        self.image = image
        self.draw = ImageDraw.Draw(image, "RGBA")
        scale = max(image.size) / 1000
        self.line_width = max(2, round(4 * scale))
        self.radius = max(3, round(6 * scale))
        size = max(12, round(22 * scale))
        try:
            self.font = ImageFont.truetype(str(FONT_PATH), size)
        except OSError:
            self.font = ImageFont.load_default(size=size)

    def line(self, a: Point, b: Point, color, width: int | None = None) -> None:
        self.draw.line([a, b], fill=color, width=width or self.line_width)

    def dashed(self, a: Point, b: Point, color, dash: float | None = None) -> None:
        dash = dash or self.line_width * 4
        length = math.dist(a, b)
        if length == 0:
            return
        steps = int(length // dash)
        for i in range(0, steps, 2):
            t0, t1 = i * dash / length, min(1.0, (i + 1) * dash / length)
            self.line(
                (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1),
                color,
                max(2, self.line_width * 2 // 3),
            )

    def joint(self, p: Point, outline) -> None:
        r = self.radius
        self.draw.ellipse(
            [p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=JOINT_FILL, outline=outline, width=max(1, r // 2)
        )

    def label(self, p: Point, text: str, color) -> None:
        left, top, right, bottom = self.draw.textbbox((0, 0), text, font=self.font)
        pad = self.radius
        w, h = right - left + 2 * pad, bottom - top + 2 * pad
        x = min(max(0, p[0]), self.image.width - w)
        y = min(max(0, p[1] - h / 2), self.image.height - h)
        self.draw.rounded_rectangle([x, y, x + w, y + h], radius=pad, fill=(255, 255, 255, 225), outline=color, width=2)
        self.draw.text((x + pad - left, y + pad - top), text, font=self.font, fill=color[:3])


def annotate(image: Image.Image, result: PostureResult) -> bytes:
    """Returns a JPEG of the photo with the analysis drawn on it."""
    if not result.usable or result.pose is None or result.view is None:
        raise ValueError("only usable results can be annotated")
    canvas = _Canvas(image.convert("RGB").copy())
    pose = result.pose

    # Draw visible skeleton segments only
    for a, b in SKELETON:
        if (
            pose[a].in_frame
            and pose[b].in_frame
            and min(pose[a].confidence, pose[b].confidence) >= MIN_DRAW_CONFIDENCE
        ):
            canvas.line(pose[a].xy, pose[b].xy, SKELETON_COLOR)
    for index in {i for pair in SKELETON for i in pair}:
        if pose[index].in_frame and pose[index].confidence >= MIN_DRAW_CONFIDENCE:
            canvas.joint(pose[index].xy, SKELETON_COLOR)

    measured = {m.metric: m for m in result.measurements}
    severity = {f.metric: f.severity for f in result.findings}

    def color(metric: str):
        return SEVERITY_COLORS[severity.get(metric)]

    offset = canvas.radius * 3
    if result.view.is_side:
        lm = side_landmarks(near_side(result.view))
        ear = pose[lm["ear"]].xy
        shoulder = pose[lm["shoulder"]].xy

        if "head_forward_angle" in measured and pose[lm["ear"]].in_frame and pose[lm["shoulder"]].in_frame:
            reach = math.dist(shoulder, ear) * 1.2
            canvas.dashed(shoulder, (shoulder[0], shoulder[1] - reach), REFERENCE_COLOR)
            canvas.line(shoulder, ear, color("head_forward_angle"))
            canvas.label(
                (ear[0] + offset, ear[1]),
                f"Head {measured['head_forward_angle'].value:.0f}°",
                color("head_forward_angle"),
            )
        if "trunk_inclination" in measured and pose[lm["hip"]].in_frame and pose[lm["shoulder"]].in_frame:
            hip = pose[lm["hip"]].xy
            canvas.dashed(hip, (hip[0], shoulder[1]), REFERENCE_COLOR)
            canvas.line(hip, shoulder, color("trunk_inclination"))
            trunk_mid = midpoint(hip, shoulder)
            canvas.label(
                (trunk_mid[0] + offset, trunk_mid[1]),
                f"Trunk {measured['trunk_inclination'].value:.0f}°",
                color("trunk_inclination"),
            )
        if (
            "hip_line_deviation" in measured
            and pose[lm["hip"]].in_frame
            and pose[lm["shoulder"]].in_frame
            and pose[lm["ankle"]].in_frame
        ):
            hip = pose[lm["hip"]].xy
            ankle = pose[lm["ankle"]].xy
            canvas.dashed(shoulder, ankle, REFERENCE_COLOR)
            canvas.label(
                (hip[0] + offset, hip[1] + offset * 2),
                f"Hip {measured['hip_line_deviation'].value:.0f}°",
                color("hip_line_deviation"),
            )
    else:
        pairs = (
            ("head_tilt", LM.LEFT_EAR, LM.RIGHT_EAR, "Head"),
            ("shoulder_tilt", LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER, "Shoulders"),
            ("hip_tilt", LM.LEFT_HIP, LM.RIGHT_HIP, "Hips"),
        )
        for metric, a, b, name in pairs:
            if metric not in measured or not (pose[a].in_frame and pose[b].in_frame):
                continue
            pa, pb = pose[a].xy, pose[b].xy
            mid = midpoint(pa, pb)
            half = math.dist(pa, pb) * 0.75
            canvas.dashed((mid[0] - half, mid[1]), (mid[0] + half, mid[1]), REFERENCE_COLOR)
            canvas.line(pa, pb, color(metric))
            canvas.label((max(pa[0], pb[0]) + offset, mid[1]), f"{name} {measured[metric].value:.1f}°", color(metric))

        if (
            "trunk_lateral_lean" in measured
            and pose[LM.LEFT_SHOULDER].in_frame
            and pose[LM.RIGHT_SHOULDER].in_frame
            and pose[LM.LEFT_HIP].in_frame
            and pose[LM.RIGHT_HIP].in_frame
        ):
            mid_sh = midpoint(pose[LM.LEFT_SHOULDER].xy, pose[LM.RIGHT_SHOULDER].xy)
            mid_hip = midpoint(pose[LM.LEFT_HIP].xy, pose[LM.RIGHT_HIP].xy)
            canvas.dashed(mid_hip, (mid_hip[0], mid_sh[1]), REFERENCE_COLOR)
            canvas.line(mid_hip, mid_sh, color("trunk_lateral_lean"))
            trunk_mid = midpoint(mid_hip, mid_sh)
            canvas.label(
                (min(pose[LM.LEFT_HIP].x, pose[LM.RIGHT_HIP].x) - offset * 6, trunk_mid[1]),
                f"Trunk {measured['trunk_lateral_lean'].value:.1f}°",
                color("trunk_lateral_lean"),
            )

    # Scope indicator tag
    scope_text = f"Scope: {result.analysis_scope.replace('_', ' ').title()}"
    canvas.label((canvas.radius * 2, canvas.radius * 2), scope_text, (30, 41, 59, 255))

    buffer = BytesIO()
    canvas.image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
