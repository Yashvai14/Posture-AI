"""Posture measurements from landmarks. A metric is only reported when the camera view supports it
and every landmark it uses is in-frame and confidently located.

Never hallucinates or estimates missing anatomical coordinates.
"""

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
from app.posture.thresholds import MIN_METRIC_CONFIDENCE

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
        candidates, view_unavailable = _side_metrics(pose, view)
        unavailable = [UnavailableMetric(m, "Needs a photo taken from the front or back.") for m in FRONTAL_METRICS]
        unavailable.extend(view_unavailable)
    else:
        candidates, view_unavailable = _frontal_metrics(pose, view)
        unavailable = [UnavailableMetric(m, "Needs a photo taken from the side.") for m in SIDE_METRICS]
        unavailable.extend(view_unavailable)

    measurements = []
    for measurement in candidates:
        if measurement.confidence >= MIN_METRIC_CONFIDENCE:
            measurements.append(measurement)
        else:
            unavailable.append(
                UnavailableMetric(
                    measurement.metric,
                    "The body points needed were not clearly visible.",
                )
            )
    return measurements, unavailable


def _side_metrics(pose: Pose, view: View) -> tuple[list[Measurement], list[UnavailableMetric]]:
    lm = side_landmarks(near_side(view))
    ear, shoulder, hip, ankle = (pose[lm[k]] for k in ("ear", "shoulder", "hip", "ankle"))
    # +1 when the person faces the right of the image: the nose is further right than the ear.
    forward = 1.0 if pose[LM.NOSE].x > ear.x else -1.0
    facing = "right" if forward > 0 else "left"
    details = {"side": near_side(view), "facing": facing}

    measurements: list[Measurement] = []
    unavailable: list[UnavailableMetric] = []

    # 1. Head forward angle
    if ear.in_frame and shoulder.in_frame:
        head = forward * angle_from_vertical(ear.xy, shoulder.xy)
        measurements.append(
            Measurement(
                "head_forward_angle",
                round(head, 1),
                "degrees",
                _confidence(pose, lm["ear"], lm["shoulder"]),
                {**details, "reference": "vertical through the shoulder; positive = ear forward of shoulder"},
            )
        )
    else:
        unavailable.append(UnavailableMetric("head_forward_angle", "Ear and shoulder points were not both visible."))

    # 2. Trunk inclination
    if shoulder.in_frame and hip.in_frame:
        trunk = forward * angle_from_vertical(shoulder.xy, hip.xy)
        measurements.append(
            Measurement(
                "trunk_inclination",
                round(trunk, 1),
                "degrees",
                _confidence(pose, lm["shoulder"], lm["hip"]),
                {**details, "reference": "vertical through the hip; positive = leaning forward"},
            )
        )
    else:
        unavailable.append(UnavailableMetric("trunk_inclination", "Hip markers were outside the frame."))

    # 3. Hip line deviation
    if shoulder.in_frame and hip.in_frame and ankle.in_frame:
        bend = 180.0 - interior_angle(shoulder.xy, hip.xy, ankle.xy)
        hip_offset = forward * horizontal_offset_from_line(hip.xy, ankle.xy, shoulder.xy)
        hip_deviation = bend if hip_offset >= 0 else -bend
        measurements.append(
            Measurement(
                "hip_line_deviation",
                round(hip_deviation, 1),
                "degrees",
                _confidence(pose, lm["shoulder"], lm["hip"], lm["ankle"]),
                {**details, "reference": "shoulder–ankle line; positive = hips forward of the line"},
            )
        )
    else:
        unavailable.append(
            UnavailableMetric("hip_line_deviation", "Lower body (knees/ankles) was outside the camera frame.")
        )

    return measurements, unavailable


def _person_side_of_image_right(view: View) -> str:
    """Which of the person's sides appears on the right of the image."""
    return "left" if view == View.FRONT else "right"


def _higher_side(tilt: float, view: View) -> str:
    right_of_image = _person_side_of_image_right(view)
    left_of_image = "right" if right_of_image == "left" else "left"
    return right_of_image if tilt > 0 else left_of_image


def _frontal_metrics(pose: Pose, view: View) -> tuple[list[Measurement], list[UnavailableMetric]]:
    measurements: list[Measurement] = []
    unavailable: list[UnavailableMetric] = []

    # Shoulder tilt
    if pose[LM.LEFT_SHOULDER].in_frame and pose[LM.RIGHT_SHOULDER].in_frame:
        tilt = tilt_from_horizontal(pose[LM.LEFT_SHOULDER].xy, pose[LM.RIGHT_SHOULDER].xy)
        measurements.append(
            Measurement(
                "shoulder_tilt",
                round(abs(tilt), 1),
                "degrees",
                _confidence(pose, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER),
                {"higher_side": _higher_side(tilt, view) if abs(tilt) >= 0.5 else "level"},
            )
        )
    else:
        unavailable.append(UnavailableMetric("shoulder_tilt", "Both shoulders were not in frame."))

    # Hip tilt
    if pose[LM.LEFT_HIP].in_frame and pose[LM.RIGHT_HIP].in_frame:
        tilt = tilt_from_horizontal(pose[LM.LEFT_HIP].xy, pose[LM.RIGHT_HIP].xy)
        measurements.append(
            Measurement(
                "hip_tilt",
                round(abs(tilt), 1),
                "degrees",
                _confidence(pose, LM.LEFT_HIP, LM.RIGHT_HIP),
                {"higher_side": _higher_side(tilt, view) if abs(tilt) >= 0.5 else "level"},
            )
        )
    else:
        unavailable.append(UnavailableMetric("hip_tilt", "Hips were outside the camera frame."))

    # Head tilt
    if pose[LM.LEFT_EAR].in_frame and pose[LM.RIGHT_EAR].in_frame:
        tilt = tilt_from_horizontal(pose[LM.LEFT_EAR].xy, pose[LM.RIGHT_EAR].xy)
        measurements.append(
            Measurement(
                "head_tilt",
                round(abs(tilt), 1),
                "degrees",
                _confidence(pose, LM.LEFT_EAR, LM.RIGHT_EAR),
                {"higher_side": _higher_side(tilt, view) if abs(tilt) >= 0.5 else "level"},
            )
        )
    else:
        unavailable.append(UnavailableMetric("head_tilt", "Both ears were not in frame."))

    # Trunk lateral lean
    if (
        pose[LM.LEFT_SHOULDER].in_frame
        and pose[LM.RIGHT_SHOULDER].in_frame
        and pose[LM.LEFT_HIP].in_frame
        and pose[LM.RIGHT_HIP].in_frame
    ):
        mid_shoulder = midpoint(pose[LM.LEFT_SHOULDER].xy, pose[LM.RIGHT_SHOULDER].xy)
        mid_hip = midpoint(pose[LM.LEFT_HIP].xy, pose[LM.RIGHT_HIP].xy)
        lean = angle_from_vertical(mid_shoulder, mid_hip)
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
    else:
        unavailable.append(
            UnavailableMetric("trunk_lateral_lean", "Hips were not visible to evaluate trunk verticality.")
        )

    return measurements, unavailable
