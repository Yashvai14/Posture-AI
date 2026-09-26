from datetime import UTC, datetime

from app.posture.classifier import RULES
from app.services.ollama_service import fallback_explanation
from app.services.pdf_generator import ReportData, build_report
from app.services.recommendations import LIBRARY, MAINTENANCE_IDS, build_corrective_plan


def test_every_finding_code_has_targeted_exercises():
    targeted = {code for e in LIBRARY for code in e.targets}
    for rule in RULES:
        assert rule.code in targeted, rule.code


def test_library_entries_are_complete():
    ids = [e.id for e in LIBRARY]
    assert len(ids) == len(set(ids))
    for e in LIBRARY:
        assert e.category in {"mobility", "stretch", "strength", "awareness"}
        assert e.instructions and e.duration and e.frequency and e.safety_note


def test_plan_without_findings_is_a_maintenance_routine():
    plan = build_corrective_plan([], None)
    assert [e["id"] for e in plan["exercises"]] == [e.id for e in LIBRARY if e.id in MAINTENANCE_IDS]


def test_plan_for_forward_head():
    plan = build_corrective_plan(["forward_head"], None)
    ids = {e["id"] for e in plan["exercises"]}
    assert {"chin_tucks", "deep_neck_flexor_hold", "posture_reset"} <= ids
    assert "glute_bridge" not in ids
    assert any("phone" in tip for tip in plan["workstation"])
    assert [w["week"] for w in plan["weekly_plan"]] == [1, 2, 3, 4]
    for week in plan["weekly_plan"]:
        assert set(week["exercise_ids"]) <= ids and week["exercise_ids"]
    assert len(plan["warning_signs"]) >= 5
    assert "emergency" in plan["warning_advice"]


def test_pain_in_symptoms_suggests_seeing_a_doctor():
    without = build_corrective_plan(["forward_head"], "I sit a lot")
    with_pain = build_corrective_plan(["forward_head"], "Neck pain in the evenings")
    assert len(with_pain["professional_care"]["who"]) > len(without["professional_care"]["who"])


def test_report_handles_missing_values_and_hostile_text():
    plan = build_corrective_plan(["uneven_shoulders"], None)
    finding = {
        "code": "uneven_shoulders",
        "title": "Uneven shoulder height",
        "severity": "moderate",
        "metric": "shoulder_tilt",
        "value": 5.5,
        "confidence": 0.9,
        "observation": "The shoulder line is tilted 5.5°, with the left shoulder higher.",
    }
    measurement = {"metric": "shoulder_tilt", "value": 5.5, "unit": "degrees", "confidence": 0.9, "details": {}}
    explanation = fallback_explanation("front", [measurement], [finding], plan).model_dump()
    pdf = build_report(
        ReportData(
            analysis_id="00000000-0000-0000-0000-000000000000",
            created_at=datetime.now(UTC),
            timezone="Asia/Kolkata",
            snapshot={
                "full_name": "<script>O'Brien & Co</script>",
                "age": None,
                "sex": None,
                "height_cm": None,
                "weight_kg": None,
                "symptoms": None,
            },
            view="front",
            alignment_score=None,
            measurements=[measurement],
            unavailable=[],
            findings=[finding],
            explanation=explanation,
            explanation_source="rule_based",
            explanation_model=None,
            plan=plan,
            annotated_jpeg=None,
        )
    )
    assert pdf.startswith(b"%PDF") and len(pdf) > 5000
