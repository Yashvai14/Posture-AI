"""Turns measurements into posture observations and an alignment score.

IMPORTANT: the thresholds below are screening heuristics chosen for this product. They have NOT been
clinically validated, they describe alignment patterns in a single photo, and they must never be
presented as a diagnosis. Change PIPELINE_VERSION whenever a threshold or weight changes so stored
results remain traceable.
"""

import enum
from dataclasses import asdict, dataclass

from app.posture.metrics import Measurement

PIPELINE_VERSION = "2.0.0"


class Severity(enum.StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    PRONOUNCED = "pronounced"


@dataclass(frozen=True)
class Rule:
    code: str
    title: str
    metric: str
    direction: int  # +1: positive values count, -1: negative values count, 0: magnitude
    mild: float
    moderate: float
    pronounced: float
    observation: str  # formatted with {value} and measurement details

    def excess(self, value: float) -> float:
        if self.direction == 0:
            return abs(value)
        return max(0.0, value * self.direction)

    def severity(self, value: float) -> Severity | None:
        v = self.excess(value)
        if v >= self.pronounced:
            return Severity.PRONOUNCED
        if v >= self.moderate:
            return Severity.MODERATE
        if v >= self.mild:
            return Severity.MILD
        return None


RULES: tuple[Rule, ...] = (
    Rule(
        "forward_head",
        "Forward head position",
        "head_forward_angle",
        +1,
        15,
        25,
        35,
        "The ear sits {value:.0f}° forward of the vertical line through the shoulder.",
    ),
    Rule(
        "trunk_forward_lean",
        "Forward trunk lean",
        "trunk_inclination",
        +1,
        6,
        10,
        15,
        "The trunk leans {value:.0f}° forward of vertical.",
    ),
    Rule(
        "trunk_backward_lean",
        "Backward trunk lean",
        "trunk_inclination",
        -1,
        6,
        10,
        15,
        "The trunk leans {value:.0f}° backward of vertical.",
    ),
    Rule(
        "hips_forward",
        "Hips forward of the shoulder–ankle line",
        "hip_line_deviation",
        +1,
        6,
        10,
        15,
        "The hips sit {value:.0f}° forward of the line from shoulder to ankle.",
    ),
    Rule(
        "uneven_shoulders",
        "Uneven shoulder height",
        "shoulder_tilt",
        0,
        2.5,
        5,
        8,
        "The shoulder line is tilted {value:.1f}°, with the {higher_side} shoulder higher.",
    ),
    Rule(
        "uneven_hips",
        "Uneven hip height",
        "hip_tilt",
        0,
        3,
        5,
        8,
        "The hip line is tilted {value:.1f}°, with the {higher_side} hip higher.",
    ),
    Rule(
        "head_tilt",
        "Sideways head tilt",
        "head_tilt",
        0,
        4,
        8,
        12,
        "The line between the ears is tilted {value:.1f}°, with the {higher_side} ear higher.",
    ),
    Rule(
        "lateral_trunk_lean",
        "Sideways trunk lean",
        "trunk_lateral_lean",
        0,
        3,
        6,
        10,
        "The trunk leans {value:.1f}° toward the {toward}.",
    ),
)

# Relative importance of each metric in the alignment score.
SCORE_WEIGHTS = {
    "head_forward_angle": 0.40,
    "trunk_inclination": 0.30,
    "hip_line_deviation": 0.30,
    "shoulder_tilt": 0.30,
    "hip_tilt": 0.25,
    "head_tilt": 0.20,
    "trunk_lateral_lean": 0.25,
}
# Penalties start at this fraction of the mild threshold so small improvements still show in trends.
PENALTY_START_FRACTION = 0.6
MIN_METRICS_FOR_SCORE = 2


@dataclass(frozen=True)
class Finding:
    code: str
    title: str
    severity: Severity
    metric: str
    value: float
    confidence: float
    observation: str

    def to_dict(self) -> dict:
        return asdict(self)


def classify(measurements: list[Measurement]) -> list[Finding]:
    by_metric = {m.metric: m for m in measurements}
    findings = []
    for rule in RULES:
        measurement = by_metric.get(rule.metric)
        if measurement is None:
            continue
        severity = rule.severity(measurement.value)
        if severity is None:
            continue
        findings.append(
            Finding(
                code=rule.code,
                title=rule.title,
                severity=severity,
                metric=rule.metric,
                value=measurement.value,
                confidence=measurement.confidence,
                observation=rule.observation.format(value=rule.excess(measurement.value), **measurement.details),
            )
        )
    return findings


def alignment_score(measurements: list[Measurement]) -> float | None:
    """0–100, higher is better aligned. A product-specific summary of the measured angles — not a health score."""
    by_metric = {m.metric: m for m in measurements if m.metric in SCORE_WEIGHTS}
    if len(by_metric) < MIN_METRICS_FOR_SCORE:
        return None
    total_weight = 0.0
    total_penalty = 0.0
    for metric, measurement in by_metric.items():
        penalty = 0.0
        for rule in (r for r in RULES if r.metric == metric):
            start = rule.mild * PENALTY_START_FRACTION
            fraction = (rule.excess(measurement.value) - start) / (rule.pronounced - start)
            penalty = max(penalty, min(1.0, max(0.0, fraction)))
        weight = SCORE_WEIGHTS[metric]
        total_weight += weight
        total_penalty += weight * penalty
    return round(100.0 * (1.0 - total_penalty / total_weight))
