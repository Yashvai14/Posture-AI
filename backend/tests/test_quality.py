import numpy as np
import pytest

from app.posture.landmarks import LM, View
from app.posture.quality import image_checks, pose_checks
from tests.fixtures.figures import front_figure
from tests.fixtures.poses import FRONT_STANDING, SIDE_STANDING, make_pose


@pytest.fixture(scope="module")
def figure_rgb():
    return np.asarray(front_figure())


def failed(checks):
    return [c.code for c in checks if not c.passed]


def test_good_image_passes_image_checks(figure_rgb):
    assert failed(image_checks(figure_rgb)) == []


@pytest.mark.parametrize(
    ("value", "code"),
    [(10, "lighting"), (250, "lighting")],
)
def test_too_dark_or_bright(value, code):
    rgb = np.full((800, 600, 3), value, dtype=np.uint8)
    assert code in failed(image_checks(rgb))


def test_low_contrast_and_small_images_fail():
    flat = np.full((800, 600, 3), 128, dtype=np.uint8)
    assert "contrast" in failed(image_checks(flat))
    small = np.asarray(front_figure()).copy()[::4, ::4]
    assert "resolution" in failed(image_checks(small))


def test_no_person(figure_rgb):
    checks, view = pose_checks(figure_rgb, [])
    assert failed(checks) == ["person_detected"]
    assert view is None


def test_multiple_people(figure_rgb):
    pose = make_pose(FRONT_STANDING)
    checks, view = pose_checks(figure_rgb, [pose, pose])
    assert failed(checks) == ["single_person"]
    checks, view = pose_checks(figure_rgb, [pose], additional_people=1)
    assert failed(checks) == ["single_person"]
    assert view is None


def test_body_out_of_frame(figure_rgb):
    pose = make_pose(FRONT_STANDING, {LM.LEFT_ANKLE: (354, 1100, 0), LM.RIGHT_ANKLE: (246, 1100, 0)})
    checks, view = pose_checks(figure_rgb, [pose])
    assert failed(checks) == ["full_body"]


def test_hidden_landmarks(figure_rgb):
    pose = make_pose(FRONT_STANDING, low_confidence={LM.LEFT_KNEE})
    checks, _ = pose_checks(figure_rgb, [pose])
    assert failed(checks) == ["landmarks_visible"]


def test_side_view_only_needs_near_side_landmarks(figure_rgb):
    far_side_hidden = {LM.LEFT_KNEE, LM.LEFT_ANKLE, LM.LEFT_EAR}
    checks, view = pose_checks(figure_rgb, [make_pose(SIDE_STANDING, low_confidence=far_side_hidden)])
    assert view == View.RIGHT_SIDE
    assert failed(checks) == []


def test_sitting_is_rejected(figure_rgb):
    # Thighs horizontal: knees level with the hips and in front of them.
    sitting = {
        LM.LEFT_KNEE: (500, 560, 0),
        LM.RIGHT_KNEE: (400, 560, 0),
        LM.LEFT_ANKLE: (505, 800, 0),
        LM.RIGHT_ANKLE: (405, 800, 0),
    }
    checks, view = pose_checks(figure_rgb, [make_pose(FRONT_STANDING, sitting)])
    assert failed(checks) == ["standing"]
    assert view is None


def test_small_person_is_rejected(figure_rgb):
    tiny = {lm: (x * 0.3 + 200, y * 0.3 + 300, z) for lm, (x, y, z) in FRONT_STANDING.items()}
    checks, _ = pose_checks(figure_rgb, [make_pose(tiny)])
    assert failed(checks) == ["body_size"]
