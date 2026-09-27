"""Multi-angle analysis fusion engine.

Combines measurements and findings from multiple viewpoints (Front, Side, Back)
into a unified posture assessment. Intelligently fuses compatible angles,
cross-verifies bilateral observations, and alerts when photos conflict.
"""

from dataclasses import asdict, dataclass, field
from typing import Sequence

from app.posture.classifier import Finding, Severity, alignment_score
from app.posture.landmarks import View
from app.posture.metrics import Measurement
from app.posture.pipeline import PostureResult


@dataclass(frozen=True)
class FusedFinding:
    finding_code: str
    title: str
    severity: Severity
    primary_metric: str
    value: float
    confidence: float
    supported_by_views: list[str]
    observation: str
    agreement_status: str = "consistent"  # "consistent", "verified_multi_view", "divergent"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass(frozen=True)
class MultiAngleAssessment:
    overall_alignment_score: float | None
    views_analyzed: list[str]
    view_results: dict[str, dict]
    fused_findings: list[FusedFinding]
    all_measurements: list[dict]
    inconsistencies: list[str]
    limitations: list[str]
    summary_message: str

    def to_dict(self) -> dict:
        return {
            "overall_alignment_score": self.overall_alignment_score,
            "views_analyzed": self.views_analyzed,
            "view_results": self.view_results,
            "fused_findings": [f.to_dict() for f in self.fused_findings],
            "all_measurements": self.all_measurements,
            "inconsistencies": self.inconsistencies,
            "limitations": self.limitations,
            "summary_message": self.summary_message,
        }


def fuse_posture_views(
    results: Sequence[tuple[str, PostureResult]],
) -> MultiAngleAssessment:
    """Fuses a collection of (view_label, PostureResult) pairs.

    view_label is typically 'front', 'side', 'back', 'left_side', or 'right_side'.
    """
    valid_results = [(lbl, res) for lbl, res in results if res.usable and res.view is not None]

    if not valid_results:
        return MultiAngleAssessment(
            overall_alignment_score=None,
            views_analyzed=[],
            view_results={},
            fused_findings=[],
            all_measurements=[],
            inconsistencies=["No usable images were provided for multi-angle evaluation."],
            limitations=["Capture at least one clear photograph of your posture."],
            summary_message="No usable views could be analyzed.",
        )

    views_analyzed = [lbl for lbl, _ in valid_results]
    all_measurements: list[Measurement] = []
    view_details: dict[str, dict] = {}
    limitations: list[str] = []
    inconsistencies: list[str] = []

    for lbl, res in valid_results:
        all_measurements.extend(res.measurements)
        view_details[lbl] = {
            "view": res.view.value,
            "alignment_score": res.alignment_score,
            "measurements_count": len(res.measurements),
            "findings_count": len(res.findings),
            "scope": res.analysis_scope,
        }
        for lim in res.limitations:
            if lim not in limitations:
                limitations.append(lim)

    # 1. Cross-verify multi-view observations (e.g. Front vs Back shoulder tilt)
    front_res = next((res for lbl, res in valid_results if res.view == View.FRONT), None)
    back_res = next((res for lbl, res in valid_results if res.view == View.BACK), None)

    shoulder_tilt_front = None
    shoulder_tilt_back = None
    if front_res:
        for m in front_res.measurements:
            if m.metric == "shoulder_tilt":
                shoulder_tilt_front = m
    if back_res:
        for m in back_res.measurements:
            if m.metric == "shoulder_tilt":
                shoulder_tilt_back = m

    fused_findings: list[FusedFinding] = []
    handled_codes: set[str] = set()

    # Check bilateral agreement for shoulder tilt if both front and back are present
    if shoulder_tilt_front and shoulder_tilt_back:
        diff = abs(shoulder_tilt_front.value - shoulder_tilt_back.value)
        if diff > 5.0:
            inconsistencies.append(
                f"Front view measured shoulder tilt of {shoulder_tilt_front.value:.1f}° while back view measured {shoulder_tilt_back.value:.1f}°. "
                "The available images produced inconsistent measurements. Consider retaking using the capture guide."
            )
        else:
            # Consistent agreement!
            avg_val = round((shoulder_tilt_front.value + shoulder_tilt_back.value) / 2.0, 1)
            # Find finding if mild/moderate
            finding_front = next((f for f in front_res.findings if f.code == "uneven_shoulders"), None)
            if finding_front:
                fused_findings.append(
                    FusedFinding(
                        finding_code="uneven_shoulders",
                        title=finding_front.title,
                        severity=finding_front.severity,
                        primary_metric="shoulder_tilt",
                        value=avg_val,
                        confidence=round(min(1.0, (shoulder_tilt_front.confidence + shoulder_tilt_back.confidence) / 2.0 + 0.05), 2),
                        supported_by_views=["front", "back"],
                        observation=f"Confirmed across both front and back views: shoulder tilt averages {avg_val:.1f}°.",
                        agreement_status="verified_multi_view",
                    )
                )
                handled_codes.add("uneven_shoulders")

    # Aggregate remaining unique findings
    for lbl, res in valid_results:
        for f in res.findings:
            if f.code in handled_codes:
                continue
            fused_findings.append(
                FusedFinding(
                    finding_code=f.code,
                    title=f.title,
                    severity=f.severity,
                    primary_metric=f.metric,
                    value=f.value,
                    confidence=f.confidence,
                    supported_by_views=[lbl],
                    observation=f.observation,
                    agreement_status="consistent",
                )
            )
            handled_codes.add(f.code)

    # Calculate overall alignment score across all distinct measurements
    # Remove duplicate measurements by averaging same metric
    unique_measurements_dict: dict[str, list[Measurement]] = {}
    for m in all_measurements:
        unique_measurements_dict.setdefault(m.metric, []).append(m)

    consensus_measurements: list[Measurement] = []
    for metric, m_list in unique_measurements_dict.items():
        avg_val = round(sum(m.value for m in m_list) / len(m_list), 1)
        avg_conf = round(sum(m.confidence for m in m_list) / len(m_list), 2)
        consensus_measurements.append(
            Measurement(
                metric=metric,
                value=avg_val,
                unit=m_list[0].unit,
                confidence=avg_conf,
                details=m_list[0].details,
            )
        )

    overall_score = alignment_score(consensus_measurements)

    # Create summary description
    views_str = ", ".join(v.capitalize() for v in views_analyzed)
    summary_message = (
        f"Multi-angle assessment completed analyzing {len(views_analyzed)} viewpoint(s): {views_str}."
    )
    if inconsistencies:
        summary_message += " Note: minor observation variance detected between viewpoints."

    return MultiAngleAssessment(
        overall_alignment_score=overall_score,
        views_analyzed=views_analyzed,
        view_results=view_details,
        fused_findings=fused_findings,
        all_measurements=[m.to_dict() for m in consensus_measurements],
        inconsistencies=inconsistencies,
        limitations=limitations,
        summary_message=summary_message,
    )
