"""Posture measurements from landmarks. A metric is only reported when the camera view supports it
and every landmark it uses is confidently located."""

from dataclasses import asdict, dataclass, field

from app.posture.geometry import (
    angle_from_vertical,
    horizontal_offset_from_line,
    interior_angle,
    midpoint,
    tilt_from_horizontal,
)
from app.posture.landmarks import LM, Pose, View, side_landmarks
from app.posture.quality import near_side

MIN_METRIC_CONFIDENCE = 0.5

SIDE_METRICS = ("head_forward_angle", "trunk_inclination", "hip_line_deviation")
FRONTAL_METRICS = ("shoulder_tilt", "hip_tilt", "head_tilt", "trunk_lateral_lean")

METRIC_LABELS = {
    "head_forward_angle": "Head forward angle",
    "trunk_inclination": "Trunk inclination",
    "hip_line_deviation": "Hip position vs. shoulder–ankle line",
    "shoulder_tilt": "Shoulder tilt",
    "hip_tilt": "Hip tilt",
    "head_tilt": "Head tilt",
    "trunk_lateral_lean": "Sideways trunk lean",
}


@dataclass(frozen=True)
class Measurement:
    metric: str
    value: float
    unit: str
    confidence: float
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class UnavailableMetric:
    metric: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _confidence(pose: Pose, *landmarks: LM) -> float:
    return round(min(pose[lm].confidence for lm in landmarks), 3)


def compute_metrics(pose: Pose, view: View) -> tuple[list[Measurement], list[UnavailableMetric]]:
    if view.is_side:
        candidates = _side_metrics(pose, view)
        unavailable = [UnavailableMetric(m, "Needs a photo taken from the front or back.") for m in FRONTAL_METRICS]
    else:
        candidates = _frontal_metrics(pose, view)
        unavailable = [UnavailableMetric(m, "Needs a photo taken from the side.") for m in SIDE_METRICS]

    measurements = []
    for measurement in candidates:
        if measurement.confidence >= MIN_METRIC_CONFIDENCE:
            measurements.append(measurement)
        else:
            unavailable.append(
                UnavailableMetric(measurement.metric, "The body points needed were not clearly visible.")
            )
    return measurements, unavailable


def _side_metrics(pose: Pose, view: View) -> list[Measurement]:
    lm = side_landmarks(near_side(view))
    ear, shoulder, hip, ankle = (pose[lm[k]] for k in ("ear", "shoulder", "hip", "ankle"))
    # +1 when the person faces the right of the image: the nose is further right than the ear.
    forward = 1.0 if pose[LM.NOSE].x > ear.x else -1.0
    facing = "right" if forward > 0 else "left"

    head = forward * angle_from_vertical(ear.xy, shoulder.xy)
    trunk = forward * angle_from_vertical(shoulder.xy, hip.xy)
    bend = 180.0 - interior_angle(shoulder.xy, hip.xy, ankle.xy)
    hip_offset = forward * horizontal_offset_from_line(hip.xy, ankle.xy, shoulder.xy)
    hip_deviation = bend if hip_offset >= 0 else -bend

    details = {"side": near_side(view), "facing": facing}
    return [
        Measurement(
            "head_forward_angle",
            round(head, 1),
            "degrees",
            _confidence(pose, lm["ear"], lm["shoulder"]),
            {**details, "reference": "vertical through the shoulder; positive = ear forward of shoulder"},
        ),
        Measurement(
            "trunk_inclination",
            round(trunk, 1),
            "degrees",
            _confidence(pose, lm["shoulder"], lm["hip"]),
            {**details, "reference": "vertical through the hip; positive = leaning forward"},
        ),
        Measurement(
            "hip_line_deviation",
            round(hip_deviation, 1),
            "degrees",
            _confidence(pose, lm["shoulder"], lm["hip"], lm["ankle"]),
            {**details, "reference": "shoulder–ankle line; positive = hips forward of the line"},
        ),
    ]


def _person_side_of_image_right(view: View) -> str:
    """Which of the person's sides appears on the right of the image."""
    return "left" if view == View.FRONT else "right"


def _higher_side(tilt: float, view: View) -> str:
    right_of_image = _person_side_of_image_right(view)
    left_of_image = "right" if right_of_image == "left" else "left"
    return right_of_image if tilt > 0 else left_of_image


def _frontal_metrics(pose: Pose, view: View) -> list[Measurement]:
    measurements = []
    for metric, left, right in (
        ("shoulder_tilt", LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER),
        ("hip_tilt", LM.LEFT_HIP, LM.RIGHT_HIP),
        ("head_tilt", LM.LEFT_EAR, LM.RIGHT_EAR),
    ):
        tilt = tilt_from_horizontal(pose[left].xy, pose[right].xy)
        measurements.append(
            Measurement(
                metric,
                round(abs(tilt), 1),
                "degrees",
                _confidence(pose, left, right),
                {"higher_side": _higher_side(tilt, view) if abs(tilt) >= 0.5 else "level"},
            )
        )

    mid_shoulder = midpoint(pose[LM.LEFT_SHOULDER].xy, pose[LM.RIGHT_SHOULDER].xy)
    mid_hip = midpoint(pose[LM.LEFT_HIP].xy, pose[LM.RIGHT_HIP].xy)
    lean = angle_from_vertical(mid_shoulder, mid_hip)
    # Positive lean = shoulders shifted to the image right of the hips.
    toward = _person_side_of_image_right(view) if lean > 0 else ("right" if view == View.FRONT else "left")
    measurements.append(
        Measurement(
            "trunk_lateral_lean",
            round(abs(lean), 1),
            "degrees",
            _confidence(pose, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER, LM.LEFT_HIP, LM.RIGHT_HIP),
            {"toward": toward if abs(lean) >= 0.5 else "centred"},
        )
    )
    return measurements
