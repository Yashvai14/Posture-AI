from io import BytesIO

import numpy as np
from PIL import Image
from sqlalchemy import select

from app.models.models import PostureAnalysis
from app.services.storage import get_storage
from tests.fixtures.figures import front_figure, side_figure
from tests.helpers import auth_headers, image_bytes, upload


def analyse(client, headers, image=None, **fields) -> dict:
    data = image_bytes(image) if image is not None else None
    response = upload(client, headers, data, **fields)
    assert response.status_code == 202, response.text
    return client.get(f"/api/analyses/{response.json()['id']}", headers=headers).json()


def test_completed_front_analysis(client, db):
    headers = auth_headers(client)
    result = analyse(
        client,
        headers,
        front_figure(10),
        date_of_birth="1995-06-15",
        sex="male",
        height_cm="175",
        weight_kg="70",
        symptoms="Right shoulder tightness",
    )
    assert result["status"] == "completed"
    assert result["view"] == "front"
    assert all(stage["state"] == "done" for stage in result["stages"])
    assert {m["metric"] for m in result["measurements"]} == {
        "shoulder_tilt",
        "hip_tilt",
        "head_tilt",
        "trunk_lateral_lean",
    }
    assert all(0.5 <= m["confidence"] <= 1 for m in result["measurements"])
    assert "uneven_shoulders" in {f["code"] for f in result["findings"]}
    assert {u["metric"] for u in result["unavailable_metrics"]} == {
        "head_forward_angle",
        "trunk_inclination",
        "hip_line_deviation",
    }
    assert 0 <= result["alignment_score"] <= 100
    assert result["explanation"]["source"] == "rule_based"  # Ollama is disabled in tests
    assert len(result["corrective_plan"]["weekly_plan"]) == 4
    assert result["snapshot"]["symptoms"] == "Right shoulder tightness"
    assert result["snapshot"]["age"] >= 30
    assert result["has_report"] and result["has_annotated_image"]
    assert all(c["passed"] for c in result["quality_checks"])

    profile = client.get("/api/patients/me/profile", headers=headers).json()
    assert profile["sex"] == "male" and float(profile["height_cm"]) == 175


def test_side_analysis_flags_forward_head(client):
    result = analyse(client, auth_headers(client), side_figure(60))
    assert result["status"] == "completed"
    assert result["view"] == "right_side"
    finding = next(f for f in result["findings"] if f["code"] == "forward_head")
    assert finding["severity"] in {"moderate", "pronounced"}
    assert "°" in finding["observation"]


def test_unsuitable_image_produces_no_measurements(client):
    headers = auth_headers(client)
    noise = (np.random.default_rng(1).random((900, 600, 3)) * 255).astype(np.uint8)
    result = analyse(client, headers, Image.fromarray(noise))
    assert result["status"] == "failed"
    assert result["failure_code"] == "image_unsuitable"
    assert result["failure_message"].startswith("We couldn't reliably analyze this image.")
    assert result["measurements"] == [] and result["findings"] == [] and result["alignment_score"] is None
    assert result["has_report"] is False
    assert any(stage["state"] == "failed" for stage in result["stages"])
    assert client.get(f"/api/analyses/{result['id']}/report", headers=headers).status_code == 404


def test_files_are_served_privately(client):
    headers = auth_headers(client)
    result = analyse(client, headers)
    for suffix, media_type in (
        ("/image", "image/jpeg"),
        ("/annotated-image", "image/jpeg"),
        ("/report", "application/pdf"),
    ):
        response = client.get(f"/api/analyses/{result['id']}{suffix}", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == media_type
        assert "no-store" in response.headers["cache-control"]
    assert client.get(f"/api/analyses/{result['id']}/report", headers=headers).content.startswith(b"%PDF")


def test_upload_without_optional_fields_works(client):
    """Regression: the prototype crashed with HTTP 500 when symptoms were empty."""
    result = analyse(client, auth_headers(client))
    assert result["status"] == "completed"
    assert result["snapshot"]["symptoms"] is None


def test_markup_in_symptoms_does_not_break_the_report(client):
    headers = auth_headers(client)
    result = analyse(client, headers, symptoms="<b>pain & stiffness</b> <unclosed <script>alert(1)</script> ₹ °")
    assert result["status"] == "completed"
    assert client.get(f"/api/analyses/{result['id']}/report", headers=headers).content.startswith(b"%PDF")


def test_history_shows_the_data_entered_for_each_analysis(client):
    """Regression: the prototype showed the latest profile against every past analysis."""
    headers = auth_headers(client)
    first = analyse(client, headers, symptoms="first: lower back ache", weight_kg="80")
    second = analyse(client, headers, symptoms="second: neck strain", weight_kg="75")
    items = {i["id"]: i for i in client.get("/api/analyses", headers=headers).json()["items"]}
    assert items[first["id"]]["symptoms"] == "first: lower back ache"
    assert items[second["id"]]["symptoms"] == "second: neck strain"
    assert float(client.get(f"/api/analyses/{first['id']}", headers=headers).json()["snapshot"]["weight_kg"]) == 80


def test_progress_groups_by_camera_view(client):
    headers = auth_headers(client)
    analyse(client, headers, front_figure(0))
    analyse(client, headers, front_figure(10))
    analyse(client, headers, side_figure(40))
    progress = client.get("/api/progress", headers=headers).json()
    assert len(progress["frontal"]) == 2 and len(progress["side"]) == 1
    assert progress["frontal"][0]["created_at"] <= progress["frontal"][1]["created_at"]
    assert "shoulder_tilt" in progress["frontal"][0]["metrics"]
    assert progress["metric_labels"]["head_forward_angle"] == "Head forward angle"


def test_delete_removes_records_and_files(client, db):
    headers = auth_headers(client)
    result = analyse(client, headers)
    analysis = db.scalar(select(PostureAnalysis))
    keys = [analysis.original_image_key, analysis.annotated_image_key, analysis.report.storage_key]
    assert all(get_storage().exists(k) for k in keys)
    assert client.delete(f"/api/analyses/{result['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/analyses/{result['id']}", headers=headers).status_code == 404
    assert not any(get_storage().exists(k) for k in keys)


# ---------------------------------------------------------------- upload validation


def test_rejects_unsupported_types(client):
    headers = auth_headers(client)
    png = image_bytes(front_figure())
    assert upload(client, headers, png, filename="photo.gif", content_type="image/gif").status_code == 415
    assert upload(client, headers, png, filename="photo.png", content_type="application/pdf").status_code == 415
    assert upload(client, headers, b"%PDF-1.4 not an image", filename="photo.png").status_code in (415, 422)
    gif = image_bytes(front_figure(), fmt="GIF")
    assert upload(client, headers, gif, filename="photo.png").status_code == 415


def test_rejects_corrupted_and_empty_images(client):
    headers = auth_headers(client)
    jpeg = image_bytes(front_figure(), fmt="JPEG")
    assert (
        upload(client, headers, jpeg[: len(jpeg) // 3], filename="photo.jpg", content_type="image/jpeg").status_code
        == 422
    )
    assert upload(client, headers, b"", filename="photo.jpg", content_type="image/jpeg").status_code == 422
    assert upload(client, headers, b"garbage" * 100, filename="photo.jpg", content_type="image/jpeg").status_code == 422


def test_rejects_oversized_uploads(client, settings, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    headers = auth_headers(client)
    noise = (np.random.default_rng(2).random((1400, 1000, 3)) * 255).astype(np.uint8)
    big = image_bytes(Image.fromarray(noise))
    assert len(big) > 1024 * 1024
    assert upload(client, headers, big).status_code == 413


def test_rejects_invalid_form_values(client):
    headers = auth_headers(client)
    assert upload(client, headers, height_cm="900").status_code == 422
    assert upload(client, headers, sex="unknown").status_code == 422
    assert upload(client, headers, date_of_birth="2999-01-01").status_code == 422
    assert upload(client, headers, symptoms="x" * 2001).status_code == 422


def test_exif_and_gps_metadata_are_stripped(client, db):
    headers = auth_headers(client)
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # camera make
    exif[0x8825] = {1: "N", 2: (21.0, 8.0, 45.0)}  # GPS IFD
    jpeg = image_bytes(front_figure(), fmt="JPEG", exif=exif)
    assert Image.open(BytesIO(jpeg)).getexif()  # the upload does carry metadata
    assert upload(client, headers, jpeg, filename="photo.jpg", content_type="image/jpeg").status_code == 202
    stored = get_storage().read(db.scalar(select(PostureAnalysis)).original_image_key)
    image = Image.open(BytesIO(stored))
    assert not image.getexif() and "exif" not in image.info
