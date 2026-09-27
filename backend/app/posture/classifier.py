"""Turns measurements into posture observations and an alignment score.

Uses rule-based thresholds from thresholds.py. Never allows LLM to override
or hallucinate measurements.
"""

import enum
from dataclasses import asdict, dataclass

from app.posture.confidence import calculate_finding_confidence
from app.posture.metrics import Measurement
from app.posture.thresholds import (
    MIN_METRICS_FOR_SCORE,
    PENALTY_START_FRACTION,
    POSTURE_THRESHOLDS,
    SCORE_WEIGHTS,
    PostureThreshold,
)

PIPELINE_VERSION = "2.1.0"


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
    observation: str

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


# Backward-compatible tuple of Rule objects built from POSTURE_THRESHOLDS
RULES: tuple[Rule, ...] = tuple(
    Rule(
        code=t.code,
        title=t.title,
        metric=t.metric,
        direction=t.direction,
        mild=t.mild,
        moderate=t.moderate,
        pronounced=t.pronounced,
        observation=t.observation_template,
    )
    for t in POSTURE_THRESHOLDS
)


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
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


def classify(measurements: list[Measurement]) -> list[Finding]:
    by_metric = {m.metric: m for m in measurements}
    findings: list[Finding] = []
    for rule in RULES:
        measurement = by_metric.get(rule.metric)
        if measurement is None:
            continue
        severity = rule.severity(measurement.value)
        if severity is None:
            continue

        f_conf = calculate_finding_confidence(
            measurement_confidence=measurement.confidence,
            measured_value=rule.excess(measurement.value),
            mild_threshold=rule.mild,
            moderate_threshold=rule.moderate,
        )

        findings.append(
            Finding(
                code=rule.code,
                title=rule.title,
                severity=severity,
                metric=rule.metric,
                value=measurement.value,
                confidence=f_conf,
                observation=rule.observation.format(value=rule.excess(measurement.value), **measurement.details),
            )
        )
    return findings


def alignment_score(measurements: list[Measurement]) -> float | None:
    """0–100, higher is better aligned. Normalises over the subset of visible metrics."""
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
    if total_weight <= 0:
        return None
    return round(100.0 * (1.0 - total_penalty / total_weight))
