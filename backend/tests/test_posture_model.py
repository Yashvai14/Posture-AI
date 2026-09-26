"""End-to-end tests of the real MediaPipe model on procedurally drawn figures."""

import numpy as np
import pytest
from PIL import Image, ImageFilter

from app.posture.annotator import annotate
from app.posture.landmarks import View
from app.posture.pipeline import UNSUITABLE_MESSAGE, analyze_image
from tests.fixtures.figures import BACKGROUND, front_figure, side_figure

pytestmark = pytest.mark.model


def run(detector, image: Image.Image):
    return analyze_image(np.asarray(image), detector)


def measured(result):
    return {m.metric: m for m in result.measurements}


def test_level_front_figure(pose_detector):
    result = run(pose_detector, front_figure(0))
    assert result.usable, [c.to_dict() for c in result.quality_checks if not c.passed]
    assert result.view == View.FRONT
    assert measured(result)["shoulder_tilt"].value < 2.5
    assert "uneven_shoulders" not in {f.code for f in result.findings}
    assert result.alignment_score is not None and result.alignment_score >= 90


@pytest.mark.parametrize(("tilt", "side"), [(10, "left"), (-10, "right")])
def test_tilted_shoulders_are_detected_with_the_correct_side(pose_detector, tilt, side):
    result = run(pose_detector, front_figure(tilt))
    assert result.usable
    shoulder = measured(result)["shoulder_tilt"]
    assert shoulder.details["higher_side"] == side
    finding = next(f for f in result.findings if f.code == "uneven_shoulders")
    assert f"{side} shoulder higher" in finding.observation


def test_shoulder_tilt_increases_with_drawn_tilt(pose_detector):
    values = [measured(run(pose_detector, front_figure(t)))["shoulder_tilt"].value for t in (0, 6, 10)]
    assert values == sorted(values)
    assert values[-1] - values[0] > 3


def test_side_figure_forward_head(pose_detector):
    neutral = run(pose_detector, side_figure(0))
    forward = run(pose_detector, side_figure(60))
    assert neutral.usable and forward.usable
    assert forward.view == View.RIGHT_SIDE
    assert measured(forward)["head_forward_angle"].value > measured(neutral)["head_forward_angle"].value + 10
    head = next(f for f in forward.findings if f.code == "forward_head")
    assert head.severity.value in {"moderate", "pronounced"}
    assert {u.metric for u in forward.unavailable} >= {"shoulder_tilt", "hip_tilt"}


def test_results_are_deterministic(pose_detector):
    image = side_figure(40)
    first, second = run(pose_detector, image), run(pose_detector, image)
    assert [m.to_dict() for m in first.measurements] == [m.to_dict() for m in second.measurements]
    assert first.alignment_score == second.alignment_score


def test_blank_image_is_rejected_without_measurements(pose_detector):
    rgb = np.asarray(front_figure())
    noise = (np.random.default_rng(0).random(rgb.shape) * 255).astype(np.uint8)
    result = analyze_image(noise, pose_detector)
    assert not result.usable
    assert result.measurements == [] and result.findings == [] and result.alignment_score is None
    assert result.failure_message.startswith(UNSUITABLE_MESSAGE)


def test_cropped_body_is_rejected(pose_detector):
    upper_half = front_figure().crop((0, 0, 600, 560)).resize((600, 560))
    result = run(pose_detector, upper_half)
    assert not result.usable
    assert "full_body" in [c.code for c in result.quality_checks if not c.passed]


@pytest.mark.parametrize("second", [front_figure(), side_figure(20)], ids=["front+front", "front+side"])
def test_two_people_are_rejected(pose_detector, second):
    # MediaPipe usually reports only the most prominent person, so this exercises the secondary search.
    canvas = Image.new("RGB", (1200, 1000), BACKGROUND)
    canvas.paste(front_figure(), (0, 0))
    canvas.paste(second, (600, 0))
    result = run(pose_detector, canvas)
    assert not result.usable
    assert [c.code for c in result.quality_checks if not c.passed] == ["single_person"]


def test_single_person_with_empty_space_is_not_flagged(pose_detector):
    canvas = Image.new("RGB", (1200, 1000), BACKGROUND)
    canvas.paste(front_figure(), (0, 0))
    assert run(pose_detector, canvas).usable


def test_blurred_photo_is_rejected(pose_detector):
    result = run(pose_detector, front_figure().filter(ImageFilter.GaussianBlur(9)))
    assert not result.usable


def test_annotation_produces_a_jpeg(pose_detector):
    image = side_figure(60)
    jpeg = annotate(image, run(pose_detector, image))
    assert jpeg[:3] == b"\xff\xd8\xff"
