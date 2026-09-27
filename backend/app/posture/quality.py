"""Decides whether an image can be analysed reliably. Unsuitable images never produce measurements.

Supports both strict full-body screening and visibility-aware partial/upper-body screening.
Provides structured image quality metrics (brightness, sharpness, contrast, visibility).
"""

import math
from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image

from app.posture.geometry import angle_from_vertical, midpoint
from app.posture.landmarks import BODY_PAIRS, LM, Pose, View, side_landmarks
from app.posture.thresholds import (
    BRIGHTNESS_RANGE,
    FRONTAL_MAX_YAW_DEG,
    MAX_LEG_SEGMENT_TILT_DEG,
    MAX_TRUNK_TILT_DEG,
    MIN_BODY_HEIGHT_FRACTION,
    MIN_CONTRAST,
    MIN_LANDMARK_CONFIDENCE,
    MIN_SHARPNESS,
    MIN_SHORT_SIDE_PX,
    MIN_UPPER_BODY_HEIGHT_FRACTION,
    SIDE_MIN_YAW_DEG,
)
from app.posture.visibility import (
    AnalysisScope,
    assess_visibility,
)


@dataclass(frozen=True)
class QualityCheck:
    code: str
    passed: bool
    message: str
    value: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ImageQualityScores:
    overall_quality: int  # 0 to 100
    brightness: int  # 0 to 100
    sharpness: int  # 0 to 100
    contrast: int  # 0 to 100
    resolution: int  # 0 to 100
    body_visibility: int  # 0 to 100
    pose_visibility: int  # 0 to 100
    background_quality: int  # 0 to 100

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PersonDetectionResult:
    person_detected: bool
    person_count: int
    primary_person_confidence: float
    message: str | None = None

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


def compute_image_quality_scores(rgb: np.ndarray, pose: Pose | None = None) -> ImageQualityScores:
    """Computes dedicated 0-100 quality scores for lighting, sharpness, contrast, and visibility."""
    height, width = rgb.shape[:2]
    gray = to_grayscale(rgb.astype(np.float32))
    brightness_val = float(gray.mean())
    contrast_val = float(gray.std())

    # Brightness score (ideal around 128)
    diff = abs(brightness_val - 128.0)
    brightness_score = int(round(max(0.0, min(100.0, 100.0 - (diff / 128.0) * 80.0))))

    # Contrast score
    contrast_score = int(round(max(0.0, min(100.0, (contrast_val / 50.0) * 100.0))))

    # Resolution score
    short_side = min(width, height)
    resolution_score = int(round(max(0.0, min(100.0, (short_side / 720.0) * 100.0))))

    # Sharpness score
    if pose is not None:
        raw_sharpness = person_sharpness(rgb, pose)
        body_vis_ratio = sum(1 for lm in pose.landmarks if lm.in_frame) / float(len(pose.landmarks))
        pose_vis_ratio = sum(1 for lm in pose.landmarks if lm.in_frame and lm.confidence >= MIN_LANDMARK_CONFIDENCE) / float(len(pose.landmarks))
    else:
        raw_sharpness = laplacian_variance(gray)
        body_vis_ratio = 0.0
        pose_vis_ratio = 0.0

    sharpness_score = int(round(max(0.0, min(100.0, (raw_sharpness / 40.0) * 100.0))))
    body_visibility_score = int(round(max(0.0, min(100.0, body_vis_ratio * 100.0))))
    pose_visibility_score = int(round(max(0.0, min(100.0, pose_vis_ratio * 100.0))))
    background_quality = int(round(max(0.0, min(100.0, 0.6 * contrast_score + 0.4 * brightness_score))))

    overall = int(
        round(
            0.20 * brightness_score
            + 0.20 * contrast_score
            + 0.25 * sharpness_score
            + 0.15 * resolution_score
            + 0.20 * pose_visibility_score
        )
    )

    return ImageQualityScores(
        overall_quality=overall,
        brightness=brightness_score,
        sharpness=sharpness_score,
        contrast=contrast_score,
        resolution=resolution_score,
        body_visibility=body_visibility_score,
        pose_visibility=pose_visibility_score,
        background_quality=background_quality,
    )


def laplacian_variance(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    lap = -4.0 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return float(lap.var())


def person_sharpness(rgb: np.ndarray, pose: Pose) -> float:
    """Sharpness of the person's region, normalised to a fixed crop height so image size doesn't matter."""
    points = [lm for lm in pose.landmarks if lm.in_frame]
    if not points:
        return 0.0
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    pad = 0.08 * (max(ys) - min(ys))
    height, width = rgb.shape[:2]
    left, right = max(0, int(min(xs) - pad)), min(width, int(max(xs) + pad))
    top, bottom = max(0, int(min(ys) - pad)), min(height, int(max(ys) + pad))
    if right <= left or bottom <= top:
        return 0.0
    crop = Image.fromarray(rgb[top:bottom, left:right]).convert("L")
    scale = 400 / max(1, crop.height)
    crop = crop.resize((max(8, round(crop.width * scale)), 400), Image.Resampling.BILINEAR)
    return laplacian_variance(np.asarray(crop, dtype=np.float32))


def estimate_yaw(pose: Pose) -> float:
    """Approximate body rotation relative to the camera in degrees (0 = facing camera, 90 = side-on)."""

    def pair_yaw(a: LM, b: LM) -> float:
        return math.degrees(math.atan2(abs(pose[a].z - pose[b].z), abs(pose[a].x - pose[b].x)))

    if pose[LM.LEFT_HIP].in_frame and pose[LM.RIGHT_HIP].in_frame:
        return 0.6 * pair_yaw(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER) + 0.4 * pair_yaw(LM.LEFT_HIP, LM.RIGHT_HIP)
    if pose[LM.LEFT_EAR].in_frame and pose[LM.RIGHT_EAR].in_frame:
        return 0.7 * pair_yaw(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER) + 0.3 * pair_yaw(LM.LEFT_EAR, LM.RIGHT_EAR)
    return pair_yaw(LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)


def classify_view(pose: Pose) -> tuple[View | None, float]:
    """Returns the camera view, or None when the body is turned diagonally to the camera."""
    yaw = estimate_yaw(pose)
    if yaw <= FRONTAL_MAX_YAW_DEG:
        # Facing the camera, the person's left shoulder appears on the right of the image.
        facing_camera = pose[LM.LEFT_SHOULDER].x > pose[LM.RIGHT_SHOULDER].x
        return (View.FRONT if facing_camera else View.BACK), yaw
    if yaw >= SIDE_MIN_YAW_DEG:
        if pose[LM.LEFT_HIP].in_frame and pose[LM.RIGHT_HIP].in_frame:
            left_depth = pose[LM.LEFT_SHOULDER].z + pose[LM.LEFT_HIP].z
            right_depth = pose[LM.RIGHT_SHOULDER].z + pose[LM.RIGHT_HIP].z
        else:
            left_depth = pose[LM.LEFT_SHOULDER].z + pose[LM.LEFT_EAR].z
            right_depth = pose[LM.RIGHT_SHOULDER].z + pose[LM.RIGHT_EAR].z
        return (View.LEFT_SIDE if left_depth < right_depth else View.RIGHT_SIDE), yaw
    return None, yaw


FULL_BODY_LANDMARKS = [LM.NOSE] + [lm for pair in BODY_PAIRS for lm in pair]
UPPER_BODY_LANDMARKS = [LM.NOSE, LM.LEFT_EAR, LM.RIGHT_EAR, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER]


def body_in_frame(pose: Pose) -> bool:
    return all(pose[lm].in_frame for lm in FULL_BODY_LANDMARKS)


def upper_body_in_frame(pose: Pose) -> bool:
    return all(pose[lm].in_frame for lm in UPPER_BODY_LANDMARKS)


def regions_outside_person(rgb: np.ndarray, pose: Pose, min_width_fraction: float = 0.2) -> list[np.ndarray]:
    xs = [lm.x for lm in pose.landmarks if lm.in_frame]
    ys = [lm.y for lm in pose.landmarks if lm.in_frame]
    if not xs or not ys:
        return []
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
    shoulders_ok = all(
        pose[lm].in_frame and pose[lm].confidence >= MIN_LANDMARK_CONFIDENCE
        for lm in (LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
    )
    hips_ok = pose[LM.LEFT_HIP].in_frame and pose[LM.RIGHT_HIP].in_frame
    ys = [lm.y for lm in pose.landmarks if lm.in_frame]
    if not ys:
        return False
    return shoulders_ok and (hips_ok or (max(ys) - min(ys)) >= 0.25 * pose.image_height)


def near_side(view: View) -> str:
    return "left" if view == View.LEFT_SIDE else "right"


def required_landmarks(view: View, scope: AnalysisScope = AnalysisScope.FULL_BODY) -> list[LM]:
    if scope in (AnalysisScope.UPPER_BODY, AnalysisScope.SEATED):
        if view.is_side:
            side = near_side(view)
            return [side_landmarks(side)["ear"], side_landmarks(side)["shoulder"]]
        return [LM.LEFT_EAR, LM.RIGHT_EAR, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER]

    if view.is_side:
        return list(side_landmarks(near_side(view)).values())
    return [lm for pair in BODY_PAIRS for lm in pair]


def _fail(code: str, message: str, value: float | None = None) -> QualityCheck:
    return QualityCheck(code, False, message, value)


def pose_checks(
    rgb: np.ndarray,
    poses: list[Pose],
    additional_people: int = 0,
    allow_partial: bool = False,
) -> tuple[list[QualityCheck], View | None]:
    """Checks that depend on detected landmarks. Stops at the first failure.

    When `allow_partial` is False (default), strictly requires full body in-frame.
    When `allow_partial` is True, permits valid upper-body screenings when lower limbs are out of frame.
    """
    checks: list[QualityCheck] = []
    if not poses:
        return [_fail("person_detected", "No person could be detected in the photo.")], None
    checks.append(QualityCheck("person_detected", True, "A person was detected."))
    pose = poses[0]

    # Handle full-body vs partial-body allowance
    if not allow_partial:
        if not body_in_frame(pose):
            return checks + [
                _fail("full_body", "Your full body is not in the frame. Make sure your head and both feet are visible.")
            ], None
        checks.append(QualityCheck("full_body", True, "The full body is in the frame."))
        scope = AnalysisScope.FULL_BODY
    else:
        vis = assess_visibility(pose)
        if vis.analysis_scope == AnalysisScope.UNUSABLE:
            return checks + [
                _fail(
                    "body_visibility",
                    "Could not detect enough clear landmarks. Ensure at least your head and shoulders are clearly visible.",
                )
            ], None
        is_full = (vis.analysis_scope == AnalysisScope.FULL_BODY)
        checks.append(
            QualityCheck(
                "full_body" if is_full else "partial_body",
                True,
                "The full body is in the frame."
                if is_full
                else "Upper-body visible. Partial upper-body posture screening will be conducted.",
            )
        )
        scope = vis.analysis_scope

    if len(poses) > 1 or additional_people > 0:
        return checks + [
            _fail("single_person", "Please upload an image containing only one person.")
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

    req = required_landmarks(view, scope=scope)
    weakest = min(pose[lm].confidence for lm in req) if req else 0.0
    if weakest < MIN_LANDMARK_CONFIDENCE:
        return checks + [
            _fail(
                "landmarks_visible",
                "Some key body points are hidden. Wear fitted clothing and ensure your upper body is unblocked.",
                weakest,
            )
        ], None
    checks.append(QualityCheck("landmarks_visible", True, "Key body points are clearly visible.", weakest))

    # Height fraction check
    if scope == AnalysisScope.FULL_BODY:
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
    else:
        # Partial / upper body
        valid_ys = [pose[lm].y for lm in UPPER_BODY_LANDMARKS if pose[lm].in_frame]
        fraction = (max(valid_ys) - min(valid_ys)) / pose.image_height if len(valid_ys) >= 2 else 0.0
        if fraction < MIN_UPPER_BODY_HEIGHT_FRACTION:
            return checks + [
                _fail(
                    "body_size",
                    "Your upper body appears too small in the frame. Move closer to the camera.",
                    fraction,
                )
            ], None
        checks.append(QualityCheck("body_size", True, "Upper body size in the frame is sufficient.", fraction))

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
