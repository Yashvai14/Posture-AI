"""Decides whether an image can be analysed reliably. Unsuitable images never produce measurements."""

import math
from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image

from app.posture.geometry import angle_from_vertical, midpoint
from app.posture.landmarks import BODY_PAIRS, LM, Pose, View, side_landmarks

MIN_SHORT_SIDE_PX = 360
BRIGHTNESS_RANGE = (35.0, 225.0)
MIN_CONTRAST = 18.0
MIN_SHARPNESS = 8.0
MIN_LANDMARK_CONFIDENCE = 0.5
MIN_BODY_HEIGHT_FRACTION = 0.45
MAX_LEG_SEGMENT_TILT_DEG = 30.0
MAX_TRUNK_TILT_DEG = 35.0
# Body rotation relative to the camera, estimated from landmark depth.
FRONTAL_MAX_YAW_DEG = 30.0
SIDE_MIN_YAW_DEG = 55.0


@dataclass(frozen=True)
class QualityCheck:
    code: str
    passed: bool
    message: str
    value: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def to_grayscale(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def image_checks(rgb: np.ndarray) -> list[QualityCheck]:
    height, width = rgb.shape[:2]
    gray = to_grayscale(rgb.astype(np.float32))
    brightness = float(gray.mean())
    contrast = float(gray.std())

    checks = [
        QualityCheck(
            "resolution",
            min(width, height) >= MIN_SHORT_SIDE_PX,
            "Resolution is sufficient."
            if min(width, height) >= MIN_SHORT_SIDE_PX
            else f"The photo is too small ({width}×{height}). "
            f"Use a photo at least {MIN_SHORT_SIDE_PX} pixels on its shorter side.",
            float(min(width, height)),
        )
    ]
    if brightness < BRIGHTNESS_RANGE[0]:
        checks.append(
            QualityCheck("lighting", False, "The photo is too dark. Retake it in good, even lighting.", brightness)
        )
    elif brightness > BRIGHTNESS_RANGE[1]:
        checks.append(
            QualityCheck(
                "lighting", False, "The photo is overexposed. Avoid strong light behind or in front of you.", brightness
            )
        )
    else:
        checks.append(QualityCheck("lighting", True, "Lighting is adequate.", brightness))
    checks.append(
        QualityCheck(
            "contrast",
            contrast >= MIN_CONTRAST,
            "Contrast is adequate."
            if contrast >= MIN_CONTRAST
            else "The photo has very low contrast. Stand against a plain background that differs from your clothing.",
            contrast,
        )
    )
    return checks


def laplacian_variance(gray: np.ndarray) -> float:
    lap = -4.0 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return float(lap.var())


def person_sharpness(rgb: np.ndarray, pose: Pose) -> float:
    """Sharpness of the person's region, normalised to a fixed crop height so image size doesn't matter."""
    points = [lm for lm in pose.landmarks if lm.in_frame]
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    pad = 0.08 * (max(ys) - min(ys))
    height, width = rgb.shape[:2]
    left, right = max(0, int(min(xs) - pad)), min(width, int(max(xs) + pad))
    top, bottom = max(0, int(min(ys) - pad)), min(height, int(max(ys) + pad))
    crop = Image.fromarray(rgb[top:bottom, left:right]).convert("L")
    scale = 400 / max(1, crop.height)
    crop = crop.resize((max(8, round(crop.width * scale)), 400), Image.Resampling.BILINEAR)
    return laplacian_variance(np.asarray(crop, dtype=np.float32))


def estimate_yaw(pose: Pose) -> float:
    """Approximate body rotation relative to the camera in degrees (0 = facing camera, 90 = side-on)."""

    def pair_yaw(a: LM, b: LM) -> float:
        return math.degrees(math.atan2(abs(pose[a].z - pose[b].z), abs(pose[a].x - pose[b].x)))

    return 0.6 * pair_yaw(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER) + 0.4 * pair_yaw(LM.LEFT_HIP, LM.RIGHT_HIP)


def classify_view(pose: Pose) -> tuple[View | None, float]:
    """Returns the camera view, or None when the body is turned diagonally to the camera."""
    yaw = estimate_yaw(pose)
    if yaw <= FRONTAL_MAX_YAW_DEG:
        # Facing the camera, the person's left shoulder appears on the right of the image.
        facing_camera = pose[LM.LEFT_SHOULDER].x > pose[LM.RIGHT_SHOULDER].x
        return (View.FRONT if facing_camera else View.BACK), yaw
    if yaw >= SIDE_MIN_YAW_DEG:
        left_depth = pose[LM.LEFT_SHOULDER].z + pose[LM.LEFT_HIP].z
        right_depth = pose[LM.RIGHT_SHOULDER].z + pose[LM.RIGHT_HIP].z
        return (View.LEFT_SIDE if left_depth < right_depth else View.RIGHT_SIDE), yaw
    return None, yaw


FULL_BODY_LANDMARKS = [LM.NOSE] + [lm for pair in BODY_PAIRS for lm in pair]


def body_in_frame(pose: Pose) -> bool:
    return all(pose[lm].in_frame for lm in FULL_BODY_LANDMARKS)


def regions_outside_person(rgb: np.ndarray, pose: Pose, min_width_fraction: float = 0.2) -> list[np.ndarray]:
    """Image regions that exclude the detected person, used to look for other people.

    The pose detector favours one prominent person, so a second person is searched for in the image with the
    first person masked out and in the strips to the left and right of them (keeping a second person at a
    detectable scale).
    """
    xs = [lm.x for lm in pose.landmarks if lm.in_frame]
    ys = [lm.y for lm in pose.landmarks if lm.in_frame]
    height, width = rgb.shape[:2]
    pad = 0.12 * (max(ys) - min(ys))
    left, right = max(0, int(min(xs) - pad)), min(width, int(max(xs) + pad))
    top, bottom = max(0, int(min(ys) - pad)), min(height, int(max(ys) + pad))
    masked = rgb.copy()
    masked[top:bottom, left:right] = np.median(rgb.reshape(-1, 3), axis=0).astype(np.uint8)
    regions = [masked]
    if left >= min_width_fraction * width:
        regions.append(np.ascontiguousarray(rgb[:, :left]))
    if width - right >= min_width_fraction * width:
        regions.append(np.ascontiguousarray(rgb[:, right:]))
    return regions


def looks_like_person(pose: Pose) -> bool:
    """Filters out fragments (e.g. a hand) the detector may report in a cropped region."""
    shoulders_ok = all(
        pose[lm].in_frame and pose[lm].confidence >= MIN_LANDMARK_CONFIDENCE
        for lm in (LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    )
    hips_ok = pose[LM.LEFT_HIP].in_frame and pose[LM.RIGHT_HIP].in_frame
    ys = [lm.y for lm in pose.landmarks if lm.in_frame]
    return shoulders_ok and hips_ok and (max(ys) - min(ys)) >= 0.3 * pose.image_height


def near_side(view: View) -> str:
    return "left" if view == View.LEFT_SIDE else "right"


def required_landmarks(view: View) -> list[LM]:
    if view.is_side:
        return list(side_landmarks(near_side(view)).values())
    return [lm for pair in BODY_PAIRS for lm in pair]


def _fail(code: str, message: str, value: float | None = None) -> QualityCheck:
    return QualityCheck(code, False, message, value)


def pose_checks(
    rgb: np.ndarray, poses: list[Pose], additional_people: int = 0
) -> tuple[list[QualityCheck], View | None]:
    """Checks that depend on detected landmarks. Stops at the first failure, since later checks would be meaningless.

    `additional_people` is the number of other people found outside the main person (see regions_outside_person).
    """
    checks: list[QualityCheck] = []
    if not poses:
        return [_fail("person_detected", "No person could be detected in the photo.")], None
    checks.append(QualityCheck("person_detected", True, "A person was detected."))
    pose = poses[0]

    if not body_in_frame(pose):
        return checks + [
            _fail("full_body", "Your full body is not in the frame. Make sure your head and both feet are visible.")
        ], None
    checks.append(QualityCheck("full_body", True, "The full body is in the frame."))

    if len(poses) > 1 or additional_people > 0:
        return checks + [
            _fail("single_person", "More than one person was detected. Make sure only you are in the photo.")
        ], None
    checks.append(QualityCheck("single_person", True, "Exactly one person is in the photo."))

    view, yaw = classify_view(pose)
    if view is None:
        return checks + [
            _fail(
                "camera_view",
                "You are turned diagonally to the camera. Face the camera directly, or stand fully side-on.",
                yaw,
            )
        ], None
    checks.append(QualityCheck("camera_view", True, f"Camera view: {view.value.replace('_', ' ')}.", yaw))

    weakest = min(pose[lm].confidence for lm in required_landmarks(view))
    if weakest < MIN_LANDMARK_CONFIDENCE:
        return checks + [
            _fail(
                "landmarks_visible",
                "Some key body points (shoulders, hips, knees or ankles) are hidden. "
                "Wear fitted clothing and keep your arms slightly away from your body.",
                weakest,
            )
        ], None
    checks.append(QualityCheck("landmarks_visible", True, "Key body points are clearly visible.", weakest))

    top = min(pose[LM.NOSE].y, pose[LM.LEFT_EAR].y, pose[LM.RIGHT_EAR].y)
    bottom = max(pose[LM.LEFT_ANKLE].y, pose[LM.RIGHT_ANKLE].y)
    fraction = (bottom - top) / pose.image_height
    if fraction < MIN_BODY_HEIGHT_FRACTION:
        return checks + [
            _fail(
                "body_size",
                "You appear too small in the photo. Move closer so your body fills most of the frame height.",
                fraction,
            )
        ], None
    checks.append(QualityCheck("body_size", True, "Body size in the frame is sufficient.", fraction))

    if not _is_standing(pose, view):
        return checks + [
            _fail(
                "standing",
                "The photo does not show an upright standing posture. Stand naturally with your weight on both feet.",
            )
        ], None
    checks.append(QualityCheck("standing", True, "Standing posture detected."))

    sharpness = person_sharpness(rgb, pose)
    if sharpness < MIN_SHARPNESS:
        return checks + [
            _fail("sharpness", "The photo is blurry. Hold the camera steady or use a timer.", sharpness)
        ], None
    checks.append(QualityCheck("sharpness", True, "The photo is sharp enough.", sharpness))
    return checks, view


def _is_standing(pose: Pose, view: View) -> bool:
    sides = [near_side(view)] if view.is_side else ["left", "right"]
    for side in sides:
        lm = side_landmarks(side)
        shoulder, hip, knee, ankle = (pose[lm[k]] for k in ("shoulder", "hip", "knee", "ankle"))
        if not (shoulder.y < hip.y < knee.y < ankle.y):
            return False
        if abs(angle_from_vertical(hip.xy, knee.xy)) > MAX_LEG_SEGMENT_TILT_DEG:
            return False
        if abs(angle_from_vertical(knee.xy, ankle.xy)) > MAX_LEG_SEGMENT_TILT_DEG:
            return False
    mid_shoulder = midpoint(pose[LM.LEFT_SHOULDER].xy, pose[LM.RIGHT_SHOULDER].xy)
    mid_hip = midpoint(pose[LM.LEFT_HIP].xy, pose[LM.RIGHT_HIP].xy)
    return abs(angle_from_vertical(mid_shoulder, mid_hip)) <= MAX_TRUNK_TILT_DEG
