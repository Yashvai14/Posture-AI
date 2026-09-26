"""Deterministic corrective plan built from a curated exercise library.

Exercises are general, low-intensity posture exercises with safety notes. They are selected from the
detected posture patterns; the LLM never invents or modifies them. The content should be reviewed by a
physiotherapist before clinical use.
"""

from dataclasses import asdict, dataclass

PLAN_VERSION = "1"


@dataclass(frozen=True)
class Exercise:
    id: str
    name: str
    category: str  # mobility | stretch | strength | awareness
    targets: tuple[str, ...]
    instructions: str
    duration: str
    frequency: str
    safety_note: str


LIBRARY: tuple[Exercise, ...] = (
    Exercise(
        "posture_reset",
        "Posture reset",
        "awareness",
        ("*",),
        "Sit or stand tall with your weight even on both feet. Gently lengthen through the top of your head, "
        "let your shoulders relax down and breathe normally.",
        "30 seconds",
        "Every hour of desk work",
        "This should feel relaxed, not forced.",
    ),
    Exercise(
        "mirror_check",
        "Mirror alignment check",
        "awareness",
        ("uneven_shoulders", "uneven_hips", "head_tilt", "lateral_trunk_lean"),
        "Stand in front of a mirror with your weight on both feet. Notice whether your head, shoulders and hips look "
        "level, gently correct, and hold the position while breathing normally.",
        "1 minute",
        "Once a day",
        "Aim for gentle awareness rather than a rigid position.",
    ),
    Exercise(
        "chin_tucks",
        "Chin tucks",
        "mobility",
        ("forward_head",),
        "Sit or stand tall. Keeping your eyes level, gently glide your chin straight back as if making a double chin, "
        "hold, then relax.",
        "Hold 5 seconds, 10 repetitions",
        "2–3 times a day",
        "Move gently. Stop if you feel pain, dizziness, or tingling in your arms.",
    ),
    Exercise(
        "seated_extension",
        "Seated upper-back extension",
        "mobility",
        ("forward_head", "trunk_forward_lean"),
        "Sit on a chair whose backrest reaches your shoulder blades. Support your head with your hands and gently "
        "lean back over the backrest, then return to upright.",
        "8–10 slow repetitions",
        "Once or twice a day",
        "Keep the movement small and comfortable. Skip it after recent back surgery unless your clinician agrees.",
    ),
    Exercise(
        "cat_cow",
        "Cat–cow",
        "mobility",
        ("trunk_forward_lean", "trunk_backward_lean", "hips_forward"),
        "On hands and knees, slowly round your back toward the ceiling, then gently let it dip as you lift your chest.",
        "8–10 slow cycles",
        "Once a day",
        "Stay within a comfortable range of movement.",
    ),
    Exercise(
        "doorway_chest_stretch",
        "Doorway chest stretch",
        "stretch",
        ("forward_head", "trunk_forward_lean"),
        "Place your forearms on a door frame with elbows at shoulder height. Step one foot through until you feel a "
        "gentle stretch across the chest.",
        "Hold 20–30 seconds, 3 times",
        "Once a day",
        "The stretch should feel mild. Do not force your shoulders back.",
    ),
    Exercise(
        "upper_trapezius_stretch",
        "Upper trapezius stretch",
        "stretch",
        ("forward_head", "head_tilt", "uneven_shoulders"),
        "Sit tall and gently tilt one ear toward the same-side shoulder while keeping the other shoulder relaxed. "
        "Repeat on the other side.",
        "Hold 20–30 seconds per side, twice",
        "Once a day",
        "Do not pull on your head. Stop if you feel tingling or numbness.",
    ),
    Exercise(
        "standing_side_bend",
        "Standing side bend",
        "stretch",
        ("lateral_trunk_lean", "uneven_hips", "uneven_shoulders"),
        "Stand with feet hip-width apart, reach one arm overhead and gently lean to the opposite side. "
        "Return and repeat on the other side.",
        "Hold 15–20 seconds per side, 3 times",
        "Once a day",
        "Keep your hips steady and avoid twisting.",
    ),
    Exercise(
        "kneeling_hip_flexor_stretch",
        "Kneeling hip flexor stretch",
        "stretch",
        ("hips_forward", "trunk_backward_lean"),
        "Kneel on one knee with the other foot in front. Gently tuck your pelvis and shift forward until you feel a "
        "stretch at the front of the hip of the kneeling leg.",
        "Hold 20–30 seconds per side, 2–3 times",
        "Once a day",
        "Put a cushion under your knee. Skip it if kneeling is painful.",
    ),
    Exercise(
        "wall_angels",
        "Wall angels",
        "strength",
        ("forward_head", "trunk_forward_lean", "uneven_shoulders"),
        "Stand with your back against a wall and feet slightly forward. With elbows bent, slowly slide your arms up "
        "and down the wall while keeping your head and lower back gently in contact.",
        "2 sets of 10",
        "4–5 days a week",
        "Only go as high as you can while keeping contact. Stop if your shoulder hurts.",
    ),
    Exercise(
        "prone_y_t_raises",
        "Prone Y and T raises",
        "strength",
        ("forward_head", "trunk_forward_lean"),
        "Lie face down with a folded towel under your forehead. Lift your arms into a Y shape and then a T shape by "
        "squeezing your shoulder blades together, keeping your neck long.",
        "2 sets of 8–10 of each",
        "3–4 days a week",
        "Start without weights and move slowly.",
    ),
    Exercise(
        "deep_neck_flexor_hold",
        "Deep neck flexor hold",
        "strength",
        ("forward_head",),
        "Lie on your back with knees bent. Gently nod your chin and lift your head a few millimetres off the floor, "
        "keeping the chin tucked.",
        "Hold 5–10 seconds, 5–8 repetitions",
        "3–4 days a week",
        "Stop if you feel neck pain or dizziness.",
    ),
    Exercise(
        "glute_bridge",
        "Glute bridge",
        "strength",
        ("hips_forward", "trunk_backward_lean", "uneven_hips"),
        "Lie on your back with knees bent and feet flat. Squeeze your glutes and lift your hips until your body forms "
        "a straight line from shoulders to knees, then lower slowly.",
        "2–3 sets of 10–12",
        "3–4 days a week",
        "Avoid arching your lower back at the top.",
    ),
    Exercise(
        "dead_bug",
        "Dead bug",
        "strength",
        ("hips_forward", "trunk_backward_lean", "lateral_trunk_lean"),
        "Lie on your back with arms pointing to the ceiling and knees bent at 90°. Slowly lower the opposite arm and "
        "leg while keeping your lower back gently pressed toward the floor.",
        "2 sets of 6–8 per side",
        "3–4 days a week",
        "Move slowly and reduce the range if your back lifts off the floor.",
    ),
    Exercise(
        "side_plank_knees",
        "Side plank from the knees",
        "strength",
        ("lateral_trunk_lean", "uneven_hips", "uneven_shoulders"),
        "Lie on your side propped on your forearm with knees bent. Lift your hips so your body forms a straight line "
        "from head to knees.",
        "Hold 15–30 seconds per side, 2–3 times",
        "3 days a week",
        "Keep your elbow under your shoulder. Stop if your shoulder hurts.",
    ),
    Exercise(
        "single_leg_balance",
        "Single-leg balance",
        "strength",
        ("uneven_hips", "lateral_trunk_lean"),
        "Stand next to a support, lift one foot slightly and hold your balance while keeping your hips level.",
        "Hold 20–30 seconds per side, 3 times",
        "Once a day",
        "Keep a chair or wall within reach.",
    ),
)

# Used when no posture pattern was flagged: a light maintenance routine.
MAINTENANCE_IDS = ("posture_reset", "cat_cow", "wall_angels", "glute_bridge")

WORKSTATION_GENERAL = (
    "Place the top of your screen at or slightly below eye level, about an arm's length away.",
    "Sit with your feet flat on the floor and your knees roughly level with your hips.",
    "Keep your elbows close to your body and your wrists straight while typing.",
)
WORKSTATION_TARGETED = {
    "forward_head": (
        "Raise your phone toward eye level instead of bending your neck down to it.",
        "If you use a laptop for long periods, raise it on a stand and use a separate keyboard and mouse.",
    ),
    "uneven_shoulders": (
        "Carry bags on alternate shoulders, or use a backpack with both straps.",
        "Avoid holding your phone between your ear and shoulder; use a headset for long calls.",
    ),
    "head_tilt": ("Position your screen directly in front of you rather than off to one side.",),
    "uneven_hips": ("Avoid standing with your weight on one leg for long periods.",),
    "lateral_trunk_lean": ("Take your wallet or phone out of your back pocket before sitting.",),
    "hips_forward": (
        "When standing for long periods, keep your knees soft rather than locked and shift your weight regularly.",
    ),
    "trunk_forward_lean": (
        "Use the chair's backrest; a small cushion behind your lower back can help you sit upright.",
    ),
}
SLEEP_GUIDANCE = (
    "Use a pillow that keeps your neck in line with your spine — neither tilted up nor dropping down.",
    "Side sleepers: a pillow between the knees can help keep the hips level.",
    "Back sleepers: a small pillow under the knees can ease strain on the lower back.",
)
SLEEP_TARGETED = {"forward_head": ("Avoid stacking several pillows under your head.",)}
MOVEMENT_BREAKS = (
    "Stand up and move for 2–3 minutes every 30–45 minutes of sitting.",
    "Use a timer or reminder app to prompt regular breaks.",
    "Walk or stand during phone calls when you can.",
)
WARNING_SIGNS = (
    "Severe pain, or pain that is quickly getting worse",
    "New weakness in your arms or legs",
    "Numbness, tingling or pins and needles spreading into your arms or legs",
    "Pain after a recent fall, accident or other serious injury",
    "Loss of bladder or bowel control, or numbness around the groin or buttocks",
    "Pain together with fever or unexplained weight loss, or pain that is worse at night and not eased by rest",
)
WARNING_ADVICE = (
    "If you notice any of these, stop the exercises and seek medical attention promptly. For loss of bladder or "
    "bowel control or sudden weakness, seek emergency care."
)
WHEN_TO_SEEK_CARE = (
    "Pain or stiffness lasts longer than 2–3 weeks despite these changes.",
    "Any exercise causes pain, or symptoms get worse.",
    "You have a history of spinal injury or surgery and want tailored advice.",
)


def _professionals(finding_codes: set[str], symptoms: str | None) -> list[str]:
    professionals = ["A physiotherapist, for a hands-on posture assessment and a personalised exercise programme."]
    pain_words = ("pain", "ache", "hurt", "numb", "tingl", "stiff")
    if symptoms and any(word in symptoms.lower() for word in pain_words):
        professionals.append(
            "A doctor (general physician or orthopaedic specialist) if pain continues, to check for other causes."
        )
    if {"uneven_shoulders", "uneven_hips", "lateral_trunk_lean"} & finding_codes:
        professionals.append(
            "A physiotherapist or orthopaedic specialist can check whether a side-to-side difference persists "
            "in a clinical examination."
        )
    return professionals


def _select(finding_codes: set[str]) -> list[Exercise]:
    if not finding_codes:
        return [e for e in LIBRARY if e.id in MAINTENANCE_IDS]
    chosen = [e for e in LIBRARY if "*" in e.targets or finding_codes & set(e.targets)]
    return chosen


def _weekly_plan(exercises: list[Exercise]) -> list[dict]:
    ids = {c: [e.id for e in exercises if e.category == c] for c in ("awareness", "mobility", "stretch", "strength")}
    gentle = ids["awareness"] + ids["mobility"] + ids["stretch"]
    return [
        {
            "week": 1,
            "title": "Mobility and awareness",
            "focus": "Learn the movements and notice your posture habits during the day.",
            "exercise_ids": gentle,
            "habits": ["Set a reminder to do a posture reset every hour of desk work."],
        },
        {
            "week": 2,
            "title": "Mobility and strengthening",
            "focus": "Keep the gentle exercises and add the first strengthening exercises.",
            "exercise_ids": gentle + ids["strength"][:2],
            "habits": ["Adjust your screen and chair using the workstation tips."],
        },
        {
            "week": 3,
            "title": "Strength and posture habits",
            "focus": "Build strength and make the posture habits part of your routine.",
            "exercise_ids": ids["mobility"] + ids["stretch"] + ids["strength"],
            "habits": ["Take a 2–3 minute movement break every 30–45 minutes of sitting."],
        },
        {
            "week": 4,
            "title": "Maintenance",
            "focus": "Keep a shorter routine going and check your progress.",
            "exercise_ids": ids["awareness"] + ids["stretch"][:1] + ids["strength"][:2],
            "habits": ["Repeat the PostureAI analysis with a photo taken the same way to compare results."],
        },
    ]


def build_corrective_plan(finding_codes: list[str], symptoms: str | None) -> dict:
    codes = set(finding_codes)
    exercises = _select(codes)
    workstation = list(WORKSTATION_GENERAL)
    sleep = list(SLEEP_GUIDANCE)
    for code in sorted(codes):
        workstation += WORKSTATION_TARGETED.get(code, ())
        sleep += SLEEP_TARGETED.get(code, ())
    return {
        "version": PLAN_VERSION,
        "exercises": [asdict(e) | {"targets": list(e.targets)} for e in exercises],
        "weekly_plan": _weekly_plan(exercises),
        "workstation": workstation,
        "sleep": sleep,
        "movement_breaks": list(MOVEMENT_BREAKS),
        "warning_signs": list(WARNING_SIGNS),
        "warning_advice": WARNING_ADVICE,
        "professional_care": {"when": list(WHEN_TO_SEEK_CARE), "who": _professionals(codes, symptoms)},
    }
