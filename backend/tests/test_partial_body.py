"""Tests for visibility-aware posture screening on partial-body and cropped images."""

import numpy as np
import pytest

from app.posture.classifier import alignment_score, classify
from app.posture.landmarks import LM, View
from app.posture.metrics import compute_metrics
from app.posture.quality import pose_checks
from app.posture.visibility import AnalysisScope, BodyRegion, assess_visibility
from tests.fixtures.figures import front_figure
from tests.fixtures.poses import FRONT_STANDING, SIDE_STANDING, make_pose


@pytest.fixture(scope="module")
def figure_rgb():
    return np.asarray(front_figure())


def test_upper_body_visibility_classification():
    # Only head and shoulders in-frame (hips, knees, ankles cut off beyond image height)
    partial = dict(FRONT_STANDING)
    partial[LM.LEFT_ANKLE] = (354, 1200, 0)
    partial[LM.RIGHT_ANKLE] = (246, 1200, 0)
    partial[LM.LEFT_KNEE] = (345, 1200, 0)
    partial[LM.RIGHT_KNEE] = (255, 1200, 0)
    partial[LM.LEFT_HIP] = (330, 1200, 0)
    partial[LM.RIGHT_HIP] = (270, 1200, 0)

    pose = make_pose(partial)
    vis = assess_visibility(pose)

    assert vis.body_region == BodyRegion.UPPER_BODY
    assert vis.analysis_scope == AnalysisScope.UPPER_BODY
    assert "head" in vis.available_regions
    assert "shoulders" in vis.available_regions
    assert "lower_limbs" not in vis.available_regions
    assert any("hip_tilt" == u["metric"] for u in vis.unavailable_metrics)


def test_upper_body_frontal_metrics_without_fabrication():
    # Upper-body only (hips and lower limbs cut off)
    partial = dict(FRONT_STANDING)
    partial[LM.LEFT_ANKLE] = (354, 1200, 0)
    partial[LM.RIGHT_ANKLE] = (246, 1200, 0)
    partial[LM.LEFT_KNEE] = (345, 1200, 0)
    partial[LM.RIGHT_KNEE] = (255, 1200, 0)
    partial[LM.LEFT_HIP] = (330, 1200, 0)
    partial[LM.RIGHT_HIP] = (270, 1200, 0)

    pose = make_pose(partial)
    measurements, unavailable = compute_metrics(pose, View.FRONT)

    measured_names = {m.metric for m in measurements}
    unavailable_names = {u.metric for u in unavailable}

    # Shoulders and head are in frame and measurable
    assert "shoulder_tilt" in measured_names
    assert "head_tilt" in measured_names

    # Hips are cut off, so hip_tilt and trunk_lateral_lean must NEVER be fabricated
    assert "hip_tilt" not in measured_names
    assert "trunk_lateral_lean" not in measured_names
    assert "hip_tilt" in unavailable_names
    assert "trunk_lateral_lean" in unavailable_names


def test_upper_body_side_metrics_without_fabrication():
    # Side upper body with head and shoulder, but hip, knee, and ankle out of frame
    partial_side = dict(SIDE_STANDING)
    partial_side[LM.RIGHT_ANKLE] = (300, 1200, 0)
    partial_side[LM.RIGHT_KNEE] = (300, 1200, 0)
    partial_side[LM.RIGHT_HIP] = (300, 1200, 0)

    pose = make_pose(partial_side)
    measurements, unavailable = compute_metrics(pose, View.RIGHT_SIDE)

    measured_names = {m.metric for m in measurements}
    unavailable_names = {u.metric for u in unavailable}

    assert "head_forward_angle" in measured_names
    assert "hip_line_deviation" not in measured_names
    assert "hip_line_deviation" in unavailable_names
    assert "trunk_inclination" in unavailable_names


def test_upper_body_pose_checks_with_allow_partial(figure_rgb):
    # Upper-body only pose passes pose_checks when allow_partial=True
    partial = dict(FRONT_STANDING)
    partial[LM.LEFT_ANKLE] = (354, 1200, 0)
    partial[LM.RIGHT_ANKLE] = (246, 1200, 0)
    partial[LM.LEFT_KNEE] = (345, 1200, 0)
    partial[LM.RIGHT_KNEE] = (255, 1200, 0)
    partial[LM.LEFT_HIP] = (330, 1200, 0)
    partial[LM.RIGHT_HIP] = (270, 1200, 0)

    pose = make_pose(partial)
    checks, view = pose_checks(figure_rgb, [pose], allow_partial=True)

    failed_codes = [c.code for c in checks if not c.passed]
    assert failed_codes == []
    assert view == View.FRONT


def test_seated_upper_body_visibility():
    # Hips visible, but knees and ankles out of frame
    seated = dict(FRONT_STANDING)
    seated[LM.LEFT_ANKLE] = (354, 1200, 0)
    seated[LM.RIGHT_ANKLE] = (246, 1200, 0)
    seated[LM.LEFT_KNEE] = (345, 1200, 0)
    seated[LM.RIGHT_KNEE] = (255, 1200, 0)

    pose = make_pose(seated)
    vis = assess_visibility(pose)

    assert vis.body_region == BodyRegion.SEATED_UPPER_BODY
    assert vis.analysis_scope == AnalysisScope.SEATED
    assert "head" in vis.available_regions
    assert "shoulders" in vis.available_regions
    assert "hips" in vis.available_regions


def test_alignment_score_computes_for_partial_measurements():
    # Only shoulder_tilt and head_tilt available
    partial = dict(FRONT_STANDING)
    partial[LM.LEFT_ANKLE] = (354, 1200, 0)
    partial[LM.RIGHT_ANKLE] = (246, 1200, 0)
    partial[LM.LEFT_HIP] = (330, 1200, 0)
    partial[LM.RIGHT_HIP] = (270, 1200, 0)

    pose = make_pose(partial)
    measurements, _ = compute_metrics(pose, View.FRONT)

    score = alignment_score(measurements)
    assert score is not None
    assert 0 <= score <= 100
