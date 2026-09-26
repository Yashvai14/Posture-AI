from dataclasses import dataclass, field

import numpy as np

from app.posture.classifier import Finding, alignment_score, classify
from app.posture.detector import PoseDetector
from app.posture.landmarks import Pose, View
from app.posture.metrics import Measurement, UnavailableMetric, compute_metrics
from app.posture.quality import (
    QualityCheck,
    body_in_frame,
    image_checks,
    looks_like_person,
    pose_checks,
    regions_outside_person,
)

UNSUITABLE_MESSAGE = (
    "We couldn't reliably analyze this image. Please upload a clear full-body standing photo "
    "with your entire body visible, taken from the front or from the side."
)


@dataclass
class PostureResult:
    usable: bool
    quality_checks: list[QualityCheck]
    view: View | None = None
    pose: Pose | None = None
    measurements: list[Measurement] = field(default_factory=list)
    unavailable: list[UnavailableMetric] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    alignment_score: float | None = None

    @property
    def failure_message(self) -> str | None:
        if self.usable:
            return None
        reasons = [c.message for c in self.quality_checks if not c.passed]
        return f"{UNSUITABLE_MESSAGE} Reason: {' '.join(reasons)}" if reasons else UNSUITABLE_MESSAGE


def analyze_image(rgb: np.ndarray, detector: PoseDetector) -> PostureResult:
    """Full deterministic analysis of one RGB image (H×W×3, uint8)."""
    checks = image_checks(rgb)
    if not all(c.passed for c in checks):
        return PostureResult(usable=False, quality_checks=checks)

    poses = detector.detect(rgb)
    additional = 0
    if len(poses) == 1 and body_in_frame(poses[0]):
        additional = sum(
            1
            for region in regions_outside_person(rgb, poses[0])
            for other in detector.detect(region)
            if looks_like_person(other)
        )
    more_checks, view = pose_checks(rgb, poses, additional_people=additional)
    checks += more_checks
    if view is None or not all(c.passed for c in checks):
        return PostureResult(usable=False, quality_checks=checks)

    pose = poses[0]
    measurements, unavailable = compute_metrics(pose, view)
    return PostureResult(
        usable=True,
        quality_checks=checks,
        view=view,
        pose=pose,
        measurements=measurements,
        unavailable=unavailable,
        findings=classify(measurements),
        alignment_score=alignment_score(measurements),
    )
