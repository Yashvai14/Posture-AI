"""Confidence scoring engine.

Clearly separates:
1. Image Quality (suitability of lighting, sharpness, resolution, contrast)
2. Pose Visibility (proportion of relevant body landmarks present in frame)
3. Measurement Confidence (minimum detection/presence confidence of key landmarks for a specific geometric metric)
4. Finding Confidence (statistical and geometric certainty supporting an observed posture pattern)

Never conflates or simulates these independent metrics into one misleading number.
"""

from dataclasses import asdict, dataclass
from typing import Sequence

from app.posture.thresholds import MIN_METRIC_CONFIDENCE


@dataclass(frozen=True)
class ConfidenceReport:
    image_quality_score: float  # 0 to 100
    pose_visibility_score: float  # 0 to 100
    overall_measurement_confidence: float  # 0 to 100
    finding_confidences: dict[str, float]  # finding_code -> 0 to 100
    reliability_tier: str  # "high", "moderate", "low", "unreliable"

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_measurement_confidence(landmark_confidences: Sequence[float]) -> float:
    """Calculates deterministic measurement confidence from landmark points.

    Uses a conservative minimum-weight formulation: the measurement is only as trustworthy
    as the weakest landmark contributing to its line or angle calculation.
    """
    if not landmark_confidences:
        return 0.0
    min_c = min(landmark_confidences)
    mean_c = sum(landmark_confidences) / len(landmark_confidences)
    # 70% driven by the weakest link, 30% by the average of the cluster
    confidence = 0.70 * min_c + 0.30 * mean_c
    return round(float(confidence), 3)


def calculate_finding_confidence(
    measurement_confidence: float,
    measured_value: float,
    mild_threshold: float,
    moderate_threshold: float,
) -> float:
    """Calculates finding confidence based on measurement confidence and margin from the threshold boundary.

    If a measurement is right on the boundary between normal and mild, confidence is attenuated
    because minor sensor noise could tip the classification. Deep within the severity band,
    finding confidence approaches measurement confidence.
    """
    if measurement_confidence < MIN_METRIC_CONFIDENCE:
        return 0.0

    excess = abs(measured_value) - mild_threshold
    if excess <= 0:
        return 0.0

    margin_span = max(1.0, moderate_threshold - mild_threshold)
    # Boundary buffer factor [0.75, 1.0]
    buffer_factor = min(1.0, 0.75 + 0.25 * (excess / margin_span))
    finding_conf = measurement_confidence * buffer_factor
    return round(float(finding_conf), 3)


def evaluate_reliability_tier(
    image_quality: float,
    pose_visibility: float,
    min_measurement_confidence: float,
) -> str:
    composite = 0.35 * (image_quality / 100.0) + 0.35 * (pose_visibility / 100.0) + 0.30 * min_measurement_confidence
    if composite >= 0.80:
        return "high"
    if composite >= 0.65:
        return "moderate"
    if composite >= 0.50:
        return "low"
    return "unreliable"
