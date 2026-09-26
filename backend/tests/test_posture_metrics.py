import math

import pytest

from app.posture.classifier import RULES, Severity, alignment_score, classify
from app.posture.landmarks import LM, View
from app.posture.metrics import FRONTAL_METRICS, SIDE_METRICS, Measurement, compute_metrics
from app.posture.quality import classify_view
from tests.fixtures.poses import FRONT_STANDING, SIDE_STANDING, make_pose, mirror


def by_metric(measurements):
    return {m.metric: m for m in measurements}


# ---------------------------------------------------------------- view classification


def test_view_classification():
    assert classify_view(make_pose(FRONT_STANDING))[0] == View.FRONT
    back = {lm: (600 - x, y, z) for lm, (x, y, z) in FRONT_STANDING.items()}
    assert classify_view(make_pose(back))[0] == View.BACK
    assert classify_view(make_pose(SIDE_STANDING))[0] == View.RIGHT_SIDE
    assert classify_view(make_pose(mirror(SIDE_STANDING)))[0] == View.LEFT_SIDE


def test_diagonal_body_is_not_classified():
    # Shoulders/hips rotated ~45°: depth difference equals horizontal difference.
    rotated = dict(FRONT_STANDING)
    rotated[LM.LEFT_SHOULDER] = (370, 240, -70)
    rotated[LM.RIGHT_SHOULDER] = (230, 240, 70)
    rotated[LM.LEFT_HIP] = (335, 530, -35)
    rotated[LM.RIGHT_HIP] = (265, 530, 35)
    view, yaw = classify_view(make_pose(rotated))
    assert view is None
    assert 30 < yaw < 55


# ---------------------------------------------------------------- side metrics


def test_neutral_side_pose_has_near_zero_metrics():
    measurements, unavailable = compute_metrics(make_pose(SIDE_STANDING), View.RIGHT_SIDE)
    m = by_metric(measurements)
    assert set(m) == set(SIDE_METRICS)
    assert m["head_forward_angle"].value == pytest.approx(0, abs=0.1)
    assert m["trunk_inclination"].value == pytest.approx(0, abs=0.1)
    assert abs(m["hip_line_deviation"].value) < 1
    assert {u.metric for u in unavailable} == set(FRONTAL_METRICS)


def test_forward_head_is_positive_whichever_way_the_person_faces():
    # Ear 60 px forward over a 120 px shoulder-to-ear height → atan(0.5) ≈ 26.6°.
    expected = math.degrees(math.atan2(60, 120))
    facing_right = make_pose(SIDE_STANDING, {LM.RIGHT_EAR: (360, 120, -150), LM.NOSE: (400, 130, -100)})
    m = by_metric(compute_metrics(facing_right, View.RIGHT_SIDE)[0])
    assert m["head_forward_angle"].value == pytest.approx(expected, abs=0.1)
    assert m["head_forward_angle"].details["facing"] == "right"

    facing_left = make_pose(mirror({**SIDE_STANDING, LM.RIGHT_EAR: (360, 120, -150), LM.NOSE: (400, 130, -100)}))
    m = by_metric(compute_metrics(facing_left, View.LEFT_SIDE)[0])
    assert m["head_forward_angle"].value == pytest.approx(expected, abs=0.1)
    assert m["head_forward_angle"].details["facing"] == "left"


def test_trunk_inclination_sign():
    forward = make_pose(SIDE_STANDING, {LM.RIGHT_SHOULDER: (330, 240, -200), LM.RIGHT_EAR: (330, 120, -150)})
    backward = make_pose(SIDE_STANDING, {LM.RIGHT_SHOULDER: (270, 240, -200), LM.RIGHT_EAR: (270, 120, -150)})
    assert by_metric(compute_metrics(forward, View.RIGHT_SIDE)[0])["trunk_inclination"].value > 5
    assert by_metric(compute_metrics(backward, View.RIGHT_SIDE)[0])["trunk_inclination"].value < -5


def test_hips_forward_of_shoulder_ankle_line_is_positive():
    pose = make_pose(SIDE_STANDING, {LM.RIGHT_HIP: (340, 530, -150)})
    value = by_metric(compute_metrics(pose, View.RIGHT_SIDE)[0])["hip_line_deviation"].value
    assert value > 5
    pose = make_pose(SIDE_STANDING, {LM.RIGHT_HIP: (260, 530, -150)})
    assert by_metric(compute_metrics(pose, View.RIGHT_SIDE)[0])["hip_line_deviation"].value < -5


# ---------------------------------------------------------------- frontal metrics


def test_level_front_pose():
    measurements, unavailable = compute_metrics(make_pose(FRONT_STANDING), View.FRONT)
    m = by_metric(measurements)
    assert set(m) == set(FRONTAL_METRICS)
    assert all(v.value == pytest.approx(0, abs=0.05) for v in m.values())
    assert m["shoulder_tilt"].details["higher_side"] == "level"
    assert {u.metric for u in unavailable} == set(SIDE_METRICS)


def test_shoulder_tilt_value_and_side_in_front_and_back_views():
    # Image-right shoulder raised by 200 * tan(5°).
    rise = 200 * math.tan(math.radians(5))
    pose = make_pose(FRONT_STANDING, {LM.LEFT_SHOULDER: (400, 240 - rise, 0)})
    m = by_metric(compute_metrics(pose, View.FRONT)[0])["shoulder_tilt"]
    assert m.value == pytest.approx(5, abs=0.05)
    assert m.details["higher_side"] == "left"  # facing the camera, image right is the person's left

    back = {lm: (600 - x, y, z) for lm, (x, y, z) in FRONT_STANDING.items()}
    back[LM.RIGHT_SHOULDER] = (back[LM.RIGHT_SHOULDER][0], 240 - rise, 0)  # at image right when seen from behind
    m = by_metric(compute_metrics(make_pose(back), View.BACK)[0])["shoulder_tilt"]
    assert m.value == pytest.approx(5, abs=0.05)
    assert m.details["higher_side"] == "right"


def test_lateral_trunk_lean_direction():
    shift = {LM.LEFT_SHOULDER: (430, 240, 0), LM.RIGHT_SHOULDER: (230, 240, 0)}  # shoulders move to image right
    m = by_metric(compute_metrics(make_pose(FRONT_STANDING, shift), View.FRONT)[0])["trunk_lateral_lean"]
    assert m.value > 5
    assert m.details["toward"] == "left"


def test_low_confidence_landmarks_make_metrics_unavailable():
    pose = make_pose(FRONT_STANDING, low_confidence={LM.LEFT_EAR})
    measurements, unavailable = compute_metrics(pose, View.FRONT)
    assert "head_tilt" not in by_metric(measurements)
    assert any(u.metric == "head_tilt" and "not clearly visible" in u.reason for u in unavailable)


# ---------------------------------------------------------------- classification and score


def m(metric, value, confidence=0.9, **details):
    return Measurement(metric, value, "degrees", confidence, details)


def test_rule_thresholds_are_ordered():
    for rule in RULES:
        assert 0 < rule.mild < rule.moderate < rule.pronounced, rule.code


@pytest.mark.parametrize(
    ("value", "expected"),
    [(5, None), (15, Severity.MILD), (24.9, Severity.MILD), (25, Severity.MODERATE), (40, Severity.PRONOUNCED)],
)
def test_forward_head_severity_bands(value, expected):
    findings = classify([m("head_forward_angle", value, side="right", facing="right")])
    assert (findings[0].severity if findings else None) == expected


def test_negative_head_angle_is_not_forward_head():
    assert classify([m("head_forward_angle", -30, side="right", facing="right")]) == []


def test_trunk_lean_direction_selects_rule():
    assert [f.code for f in classify([m("trunk_inclination", 12)])] == ["trunk_forward_lean"]
    assert [f.code for f in classify([m("trunk_inclination", -12)])] == ["trunk_backward_lean"]


def test_observation_text_uses_measurement_details():
    finding = classify([m("shoulder_tilt", 6.2, higher_side="left")])[0]
    assert finding.code == "uneven_shoulders"
    assert finding.severity == Severity.MODERATE
    assert "left shoulder higher" in finding.observation
    assert "6.2°" in finding.observation


def test_alignment_score_bounds_and_monotonicity():
    assert alignment_score([m("shoulder_tilt", 0)]) is None  # too few metrics
    perfect = alignment_score([m("shoulder_tilt", 0), m("hip_tilt", 0)])
    assert perfect == 100
    worse = alignment_score([m("shoulder_tilt", 4), m("hip_tilt", 0)])
    worst = alignment_score([m("shoulder_tilt", 20), m("hip_tilt", 20)])
    assert perfect > worse > worst
    assert worst == 0


def test_score_is_deterministic():
    data = [m("head_forward_angle", 22), m("trunk_inclination", 3), m("hip_line_deviation", 1)]
    assert alignment_score(data) == alignment_score(list(reversed(data)))
