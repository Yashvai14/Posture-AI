"""Complete computer vision screening pipeline for posture analysis.

Separates CV measurements from AI explanations:
1. Image Preprocessing (EXIF orientation, aspect-ratio scaling, diagnostics)
2. Person Detection (verifies single individual)
3. Visibility Assessment (classifies body region: FULL_BODY, UPPER_BODY, etc.)
4. Pose Quality & View Classification (front, back, side)
5. Geometric Posture Measurements (no hallucinated coordinates)
6. Rule-based Finding Classification & Calibration
7. Multi-layer Confidence Evaluation
"""

from dataclasses import dataclass, field

import numpy as np

from app.posture.classifier import Finding, alignment_score, classify
from app.posture.confidence import (
    ConfidenceReport,
    evaluate_reliability_tier,
)
from app.posture.detector import PoseDetector
from app.posture.landmarks import Pose, View
from app.posture.metrics import Measurement, UnavailableMetric, compute_metrics
from app.posture.preprocessing import preprocess_image
from app.posture.quality import (
    ImageQualityScores,
    QualityCheck,
    body_in_frame,
    compute_image_quality_scores,
    image_checks,
    looks_like_person,
    pose_checks,
    regions_outside_person,
)
from app.posture.visibility import (
    AnalysisScope,
    BodyRegion,
    assess_visibility,
)

UNSUITABLE_MESSAGE = (
    "We couldn't reliably analyze this image. Please upload a clear photo "
    "with good lighting and your upper or full body visible, taken from the front or side."
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
    analysis_scope: str = AnalysisScope.FULL_BODY.value
    body_region: str = BodyRegion.FULL_BODY.value
    image_quality: ImageQualityScores | None = None
    confidence_report: ConfidenceReport | None = None
    analyzable_metrics: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    @property
    def failure_message(self) -> str | None:
        if self.usable:
            return None
        reasons = [c.message for c in self.quality_checks if not c.passed]
        return f"{UNSUITABLE_MESSAGE} Reason: {' '.join(reasons)}" if reasons else UNSUITABLE_MESSAGE


def analyze_image(
    rgb: np.ndarray,
    detector: PoseDetector,
    allow_partial: bool = False,
) -> PostureResult:
    """Full deterministic analysis of one image (H×W×3, uint8)."""
    # 1. Preprocessing (EXIF rotation, dimension sanity, stats)
    prep = preprocess_image(rgb)
    processed_rgb = prep.rgb

    checks = image_checks(processed_rgb)
    if not all(c.passed for c in checks):
        return PostureResult(usable=False, quality_checks=checks)

    # 2. Pose detection
    poses = detector.detect(processed_rgb)
    if not poses:
        fail_check = QualityCheck("person_detected", False, "No person could be detected in the photo.")
        return PostureResult(usable=False, quality_checks=checks + [fail_check])

    pose = poses[0]

    # Check for multiple people
    additional = 0
    if len(poses) == 1 and body_in_frame(pose):
        additional = sum(
            1
            for region in regions_outside_person(processed_rgb, pose)
            for other in detector.detect(region)
            if looks_like_person(other)
        )

    # 3. Visibility and body region classification
    vis = assess_visibility(pose)

    # 4. Pose and quality checks
    more_checks, view = pose_checks(
        processed_rgb, poses, additional_people=additional, allow_partial=allow_partial
    )
    checks += more_checks
    if view is None or not all(c.passed for c in checks):
        return PostureResult(usable=False, quality_checks=checks)

    # 5. Measurements (only available landmarks, never hallucinates)
    measurements, unavailable = compute_metrics(pose, view)

    # Merge visibility limitations with unavailable metrics
    for u in vis.unavailable_metrics:
        if not any(m.metric == u["metric"] for m in measurements) and not any(
            un.metric == u["metric"] for un in unavailable
        ):
            unavailable.append(UnavailableMetric(metric=u["metric"], reason=u["reason"]))

    # 6. Rule-based classification
    findings = classify(measurements)
    score = alignment_score(measurements)

    # 7. Separated Quality & Confidence Scoring
    iq_scores = compute_image_quality_scores(processed_rgb, pose)
    m_confs = [m.confidence for m in measurements]
    overall_m_conf = round(float(sum(m_confs) / len(m_confs) * 100), 1) if m_confs else 0.0
    finding_confs = {f.code: round(f.confidence * 100, 1) for f in findings}

    conf_report = ConfidenceReport(
        image_quality_score=float(iq_scores.overall_quality),
        pose_visibility_score=float(iq_scores.pose_visibility),
        overall_measurement_confidence=overall_m_conf,
        finding_confidences=finding_confs,
        reliability_tier=evaluate_reliability_tier(
            float(iq_scores.overall_quality),
            float(iq_scores.pose_visibility),
            min(m_confs) if m_confs else 0.0,
        ),
    )

    return PostureResult(
        usable=True,
        quality_checks=checks,
        view=view,
        pose=pose,
        measurements=measurements,
        unavailable=unavailable,
        findings=findings,
        alignment_score=score,
        analysis_scope=vis.analysis_scope.value,
        body_region=vis.body_region.value,
        image_quality=iq_scores,
        confidence_report=conf_report,
        analyzable_metrics=vis.analyzable_metrics,
        limitations=vis.limitations,
    )
