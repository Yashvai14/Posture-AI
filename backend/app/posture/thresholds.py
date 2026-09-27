"""Configurable thresholds for computer vision screening, quality assessment, and posture classification."""

from dataclasses import dataclass


# ---------------------------------------------------------------- Image Quality Thresholds
MIN_SHORT_SIDE_PX: int = 360
MAX_IMAGE_DIMENSION_PX: int = 2048  # Resized proportionally if exceeded
BRIGHTNESS_RANGE: tuple[float, float] = (30.0, 230.0)
MIN_CONTRAST: float = 18.0
MIN_SHARPNESS: float = 8.0

# ---------------------------------------------------------------- Pose & Landmark Thresholds
MIN_LANDMARK_CONFIDENCE: float = 0.50
MIN_METRIC_CONFIDENCE: float = 0.45
MIN_FULL_BODY_HEIGHT_FRACTION: float = 0.45
MIN_BODY_HEIGHT_FRACTION: float = MIN_FULL_BODY_HEIGHT_FRACTION
MIN_UPPER_BODY_HEIGHT_FRACTION: float = 0.10
MAX_LEG_SEGMENT_TILT_DEG: float = 30.0
MAX_TRUNK_TILT_DEG: float = 35.0

# Camera view classification (yaw estimation)
FRONTAL_MAX_YAW_DEG: float = 32.0
SIDE_MIN_YAW_DEG: float = 50.0

# ---------------------------------------------------------------- Posture Classification Rules
@dataclass(frozen=True)
class PostureThreshold:
    code: str
    title: str
    metric: str
    direction: int  # +1: positive values count, -1: negative values count, 0: absolute magnitude
    mild: float
    moderate: float
    pronounced: float
    observation_template: str
    unit: str = "degrees"


POSTURE_THRESHOLDS: tuple[PostureThreshold, ...] = (
    PostureThreshold(
        code="forward_head",
        title="Forward head position",
        metric="head_forward_angle",
        direction=+1,
        mild=15.0,
        moderate=25.0,
        pronounced=35.0,
        observation_template="The ear sits {value:.0f}° forward of the vertical line through the shoulder.",
    ),
    PostureThreshold(
        code="neck_forward_lean",
        title="Forward neck inclination",
        metric="neck_inclination",
        direction=+1,
        mild=18.0,
        moderate=28.0,
        pronounced=38.0,
        observation_template="The neck inclines {value:.0f}° forward of vertical.",
    ),
    PostureThreshold(
        code="trunk_forward_lean",
        title="Forward trunk lean",
        metric="trunk_inclination",
        direction=+1,
        mild=6.0,
        moderate=10.0,
        pronounced=15.0,
        observation_template="The trunk leans {value:.0f}° forward of vertical.",
    ),
    PostureThreshold(
        code="trunk_backward_lean",
        title="Backward trunk lean",
        metric="trunk_inclination",
        direction=-1,
        mild=6.0,
        moderate=10.0,
        pronounced=15.0,
        observation_template="The trunk leans {value:.0f}° backward of vertical.",
    ),
    PostureThreshold(
        code="hips_forward",
        title="Hips forward of the shoulder–ankle line",
        metric="hip_line_deviation",
        direction=+1,
        mild=6.0,
        moderate=10.0,
        pronounced=15.0,
        observation_template="The hips sit {value:.0f}° forward of the line from shoulder to ankle.",
    ),
    PostureThreshold(
        code="uneven_shoulders",
        title="Uneven shoulder height",
        metric="shoulder_tilt",
        direction=0,
        mild=2.5,
        moderate=5.0,
        pronounced=8.0,
        observation_template="The shoulder line is tilted {value:.1f}°, with the {higher_side} shoulder higher.",
    ),
    PostureThreshold(
        code="uneven_hips",
        title="Uneven hip height",
        metric="hip_tilt",
        direction=0,
        mild=3.0,
        moderate=5.0,
        pronounced=8.0,
        observation_template="The hip line is tilted {value:.1f}°, with the {higher_side} hip higher.",
    ),
    PostureThreshold(
        code="head_tilt",
        title="Sideways head tilt",
        metric="head_tilt",
        direction=0,
        mild=4.0,
        moderate=8.0,
        pronounced=12.0,
        observation_template="The line between the ears is tilted {value:.1f}°, with the {higher_side} ear higher.",
    ),
    PostureThreshold(
        code="lateral_trunk_lean",
        title="Sideways trunk lean",
        metric="trunk_lateral_lean",
        direction=0,
        mild=3.0,
        moderate=6.0,
        pronounced=10.0,
        observation_template="The trunk leans {value:.1f}° toward the {toward}.",
    ),
    PostureThreshold(
        code="shoulder_asymmetry",
        title="Shoulder asymmetry",
        metric="shoulder_asymmetry",
        direction=0,
        mild=2.5,
        moderate=5.0,
        pronounced=8.0,
        observation_template="The shoulders demonstrate a {value:.1f}° height asymmetry.",
    ),
)

# Relative importance weights for calculating posture alignment score (0-100)
SCORE_WEIGHTS: dict[str, float] = {
    "head_forward_angle": 0.40,
    "neck_inclination": 0.35,
    "trunk_inclination": 0.30,
    "hip_line_deviation": 0.30,
    "shoulder_tilt": 0.30,
    "shoulder_asymmetry": 0.25,
    "hip_tilt": 0.25,
    "head_tilt": 0.20,
    "trunk_lateral_lean": 0.25,
}

PENALTY_START_FRACTION: float = 0.60
MIN_METRICS_FOR_SCORE: int = 2
