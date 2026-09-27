"""Unit tests for multi-angle posture fusion."""

from app.posture.classifier import Finding, Severity
from app.posture.fusion import fuse_posture_views
from app.posture.landmarks import View
from app.posture.metrics import Measurement
from app.posture.pipeline import PostureResult
from app.posture.quality import QualityCheck


def dummy_result(view: View, measurements: list[Measurement], findings: list[Finding]) -> PostureResult:
    return PostureResult(
        usable=True,
        quality_checks=[QualityCheck("test", True, "ok")],
        view=view,
        measurements=measurements,
        findings=findings,
        alignment_score=85.0,
    )


def test_fuse_front_and_side_views():
    m_front = [Measurement("shoulder_tilt", 4.0, "degrees", 0.9)]
    f_front = [Finding("uneven_shoulders", "Uneven shoulders", Severity.MILD, "shoulder_tilt", 4.0, 0.9, "Tilted")]

    m_side = [Measurement("head_forward_angle", 22.0, "degrees", 0.88)]
    f_side = [Finding("forward_head", "Forward head", Severity.MILD, "head_forward_angle", 22.0, 0.88, "Forward")]

    front_res = dummy_result(View.FRONT, m_front, f_front)
    side_res = dummy_result(View.RIGHT_SIDE, m_side, f_side)

    fused = fuse_posture_views([("front", front_res), ("side", side_res)])

    assert set(fused.views_analyzed) == {"front", "side"}
    assert len(fused.fused_findings) == 2
    f_codes = {f.finding_code for f in fused.fused_findings}
    assert "uneven_shoulders" in f_codes
    assert "forward_head" in f_codes
    assert fused.overall_alignment_score is not None


def test_fuse_front_and_back_agreement():
    m_front = [Measurement("shoulder_tilt", 4.2, "degrees", 0.9)]
    f_front = [Finding("uneven_shoulders", "Uneven shoulders", Severity.MILD, "shoulder_tilt", 4.2, 0.9, "Tilted")]

    m_back = [Measurement("shoulder_tilt", 4.0, "degrees", 0.9)]
    f_back = [Finding("uneven_shoulders", "Uneven shoulders", Severity.MILD, "shoulder_tilt", 4.0, 0.9, "Tilted")]

    front_res = dummy_result(View.FRONT, m_front, f_front)
    back_res = dummy_result(View.BACK, m_back, f_back)

    fused = fuse_posture_views([("front", front_res), ("back", back_res)])

    assert len(fused.fused_findings) == 1
    sh_finding = fused.fused_findings[0]
    assert sh_finding.finding_code == "uneven_shoulders"
    assert "front" in sh_finding.supported_by_views
    assert "back" in sh_finding.supported_by_views
    assert sh_finding.agreement_status == "verified_multi_view"


def test_fuse_detects_inconsistent_views():
    # Front sees 1.0 deg tilt, Back sees 8.5 deg tilt (divergent)
    m_front = [Measurement("shoulder_tilt", 1.0, "degrees", 0.9)]
    m_back = [Measurement("shoulder_tilt", 8.5, "degrees", 0.9)]

    front_res = dummy_result(View.FRONT, m_front, [])
    back_res = dummy_result(View.BACK, m_back, [])

    fused = fuse_posture_views([("front", front_res), ("back", back_res)])
    assert len(fused.inconsistencies) > 0
    assert "inconsistent measurements" in fused.inconsistencies[0]
