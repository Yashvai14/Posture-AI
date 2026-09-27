"""Visibility and body region classification engine.

Determines which anatomical regions are reliably visible in frame and decides the
proper analysis scope (full-body, upper-body, seated, etc.).
NEVER estimates or hallucinates coordinates for missing landmarks.
"""

import enum
from dataclasses import asdict, dataclass

from app.posture.landmarks import LM, Pose, View, side_landmarks
from app.posture.thresholds import (
    MIN_LANDMARK_CONFIDENCE,
    MIN_UPPER_BODY_HEIGHT_FRACTION,
)


class BodyRegion(enum.StrEnum):
    FULL_BODY = "FULL_BODY"
    UPPER_BODY = "UPPER_BODY"
    SEATED_UPPER_BODY = "SEATED_UPPER_BODY"
    LOWER_BODY = "LOWER_BODY"
    HEAD_NECK = "HEAD_NECK"
    PARTIAL_BODY = "PARTIAL_BODY"
    UNUSABLE = "UNUSABLE"


class AnalysisScope(enum.StrEnum):
    FULL_BODY = "full_body"
    UPPER_BODY = "upper_body"
    SEATED = "seated_upper_body"
    LOWER_BODY = "lower_body"
    UNUSABLE = "unusable"


@dataclass(frozen=True)
class RegionVisibility:
    head: bool
    neck: bool
    shoulders: bool
    upper_torso: bool
    hips: bool
    knees: bool
    ankles: bool
    feet: bool

    def available_regions_list(self) -> list[str]:
        regions = []
        if self.head:
            regions.append("head")
        if self.neck:
            regions.append("neck")
        if self.shoulders:
            regions.append("shoulders")
        if self.upper_torso:
            regions.append("upper_torso")
        if self.hips:
            regions.append("hips")
        if self.knees:
            regions.append("knees")
        if self.knees and (self.ankles or self.feet):
            regions.append("lower_limbs")
        return regions


@dataclass(frozen=True)
class BodyVisibilityAssessment:
    body_region: BodyRegion
    analysis_scope: AnalysisScope
    available_regions: list[str]
    visible_landmark_count: int
    total_landmark_count: int
    visibility_ratio: float
    analyzable_metrics: list[str]
    unavailable_metrics: list[dict[str, str]]
    limitations: list[str]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["body_region"] = self.body_region.value
        data["analysis_scope"] = self.analysis_scope.value
        return data


def is_landmark_visible(pose: Pose, lm: LM, min_conf: float = MIN_LANDMARK_CONFIDENCE) -> bool:
    """True if landmark is located inside the frame with adequate detection/presence confidence."""
    p = pose[lm]
    return bool(p.in_frame and p.confidence >= min_conf)


def assess_visibility(pose: Pose, view: View | None = None) -> BodyVisibilityAssessment:
    """Deterministically identifies visible body regions and allowable metrics."""
    # Check head
    head_ok = (
        is_landmark_visible(pose, LM.NOSE)
        or is_landmark_visible(pose, LM.LEFT_EAR)
        or is_landmark_visible(pose, LM.RIGHT_EAR)
    )

    # Check shoulders
    if view and view.is_side:
        near = side_landmarks("left" if view == View.LEFT_SIDE else "right")
        shoulders_ok = is_landmark_visible(pose, near["shoulder"])
        hips_ok = is_landmark_visible(pose, near["hip"])
        knees_ok = is_landmark_visible(pose, near["knee"])
        ankles_ok = is_landmark_visible(pose, near["ankle"])
    else:
        shoulders_ok = is_landmark_visible(pose, LM.LEFT_SHOULDER) and is_landmark_visible(pose, LM.RIGHT_SHOULDER)
        hips_ok = is_landmark_visible(pose, LM.LEFT_HIP) and is_landmark_visible(pose, LM.RIGHT_HIP)
        knees_ok = is_landmark_visible(pose, LM.LEFT_KNEE) and is_landmark_visible(pose, LM.RIGHT_KNEE)
        ankles_ok = is_landmark_visible(pose, LM.LEFT_ANKLE) and is_landmark_visible(pose, LM.RIGHT_ANKLE)

    neck_ok = head_ok and shoulders_ok
    upper_torso_ok = shoulders_ok and (
        is_landmark_visible(pose, LM.LEFT_ELBOW) or is_landmark_visible(pose, LM.RIGHT_ELBOW) or hips_ok
    )
    feet_ok = is_landmark_visible(pose, LM.LEFT_FOOT_INDEX) or is_landmark_visible(pose, LM.RIGHT_FOOT_INDEX)

    reg = RegionVisibility(
        head=head_ok,
        neck=neck_ok,
        shoulders=shoulders_ok,
        upper_torso=upper_torso_ok,
        hips=hips_ok,
        knees=knees_ok,
        ankles=ankles_ok,
        feet=feet_ok,
    )

    visible_count = sum(1 for lm in pose.landmarks if lm.in_frame and lm.confidence >= MIN_LANDMARK_CONFIDENCE)
    total_count = len(pose.landmarks)
    ratio = round(visible_count / float(total_count), 3)

    # Determine vertical span of visible upper body
    upper_lms = [pose[lm] for lm in (LM.NOSE, LM.LEFT_EAR, LM.RIGHT_EAR, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER) if lm]
    valid_ys = [p.y for p in upper_lms if p.in_frame]
    upper_span = (max(valid_ys) - min(valid_ys)) / pose.image_height if len(valid_ys) >= 2 else 0.0

    # Determine region and scope
    limitations: list[str] = []
    analyzable: list[str] = []
    unavailable: list[dict[str, str]] = []

    if shoulders_ok and hips_ok and knees_ok and ankles_ok:
        body_region = BodyRegion.FULL_BODY
        analysis_scope = AnalysisScope.FULL_BODY
    elif head_ok and shoulders_ok and upper_span >= MIN_UPPER_BODY_HEIGHT_FRACTION:
        if hips_ok and not (knees_ok and ankles_ok):
            # Hips visible but lower legs cut off - could be seated or partial
            body_region = BodyRegion.SEATED_UPPER_BODY
            analysis_scope = AnalysisScope.SEATED
            limitations.append("Lower limbs (knees/ankles) are outside the frame. Full standing alignment cannot be assessed.")
        else:
            body_region = BodyRegion.UPPER_BODY
            analysis_scope = AnalysisScope.UPPER_BODY
            limitations.append("Assessment limited to visible upper body. Lower-body measurements were not available.")
    elif hips_ok and knees_ok and ankles_ok and not shoulders_ok:
        body_region = BodyRegion.LOWER_BODY
        analysis_scope = AnalysisScope.LOWER_BODY
        limitations.append("Only lower body detected. Upper-body postural alignment cannot be assessed.")
    elif head_ok and not shoulders_ok:
        body_region = BodyRegion.HEAD_NECK
        analysis_scope = AnalysisScope.UNUSABLE
        limitations.append("Only head/neck visible without shoulders. Posture analysis requires at least visible shoulders.")
    else:
        body_region = BodyRegion.PARTIAL_BODY if visible_count >= 6 else BodyRegion.UNUSABLE
        analysis_scope = AnalysisScope.UNUSABLE
        limitations.append("Insufficient body landmarks visible for posture analysis.")

    # Populate allowable vs unavailable metrics
    if analysis_scope in (AnalysisScope.FULL_BODY, AnalysisScope.UPPER_BODY, AnalysisScope.SEATED):
        analyzable.extend(["head_alignment", "head_tilt", "shoulder_tilt", "shoulder_asymmetry", "neck_inclination"])
        if hips_ok:
            analyzable.extend(["trunk_inclination", "hip_tilt", "lateral_trunk_lean"])
        else:
            unavailable.append({
                "metric": "hip_tilt",
                "reason": "Hips were not visible in the frame."
            })
            unavailable.append({
                "metric": "lateral_trunk_lean",
                "reason": "Hips were not visible to evaluate trunk verticality."
            })
            unavailable.append({
                "metric": "trunk_inclination",
                "reason": "Hip markers were outside the frame."
            })

        if knees_ok and ankles_ok:
            analyzable.extend(["hip_line_deviation", "knee_alignment", "ankle_alignment"])
        else:
            unavailable.append({
                "metric": "hip_line_deviation",
                "reason": "Lower body (knees/ankles) was outside the camera frame."
            })
    else:
        unavailable.append({
            "metric": "all_metrics",
            "reason": "Insufficient landmarks visible for reliable screening."
        })

    return BodyVisibilityAssessment(
        body_region=body_region,
        analysis_scope=analysis_scope,
        available_regions=reg.available_regions_list(),
        visible_landmark_count=visible_count,
        total_landmark_count=total_count,
        visibility_ratio=ratio,
        analyzable_metrics=analyzable,
        unavailable_metrics=unavailable,
        limitations=limitations,
    )
