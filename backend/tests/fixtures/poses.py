"""Synthetic landmark sets with exactly known geometry for unit tests (no model involved)."""

from app.posture.landmarks import LM, NUM_LANDMARKS, Landmark, Pose

WIDTH, HEIGHT = 600, 1000

# A symmetric person facing the camera: (x, y, z) in pixels.
FRONT_STANDING: dict[LM, tuple[float, float, float]] = {
    LM.NOSE: (300, 120, -60),
    LM.LEFT_EYE: (320, 105, -55),
    LM.RIGHT_EYE: (280, 105, -55),
    LM.LEFT_EAR: (355, 115, 0),
    LM.RIGHT_EAR: (245, 115, 0),
    LM.LEFT_SHOULDER: (400, 240, 0),
    LM.RIGHT_SHOULDER: (200, 240, 0),
    LM.LEFT_ELBOW: (420, 390, 0),
    LM.RIGHT_ELBOW: (180, 390, 0),
    LM.LEFT_WRIST: (425, 520, 0),
    LM.RIGHT_WRIST: (175, 520, 0),
    LM.LEFT_HIP: (350, 530, 0),
    LM.RIGHT_HIP: (250, 530, 0),
    LM.LEFT_KNEE: (352, 720, 0),
    LM.RIGHT_KNEE: (248, 720, 0),
    LM.LEFT_ANKLE: (354, 900, 0),
    LM.RIGHT_ANKLE: (246, 900, 0),
    LM.LEFT_HEEL: (350, 925, 0),
    LM.RIGHT_HEEL: (250, 925, 0),
    LM.LEFT_FOOT_INDEX: (360, 945, -30),
    LM.RIGHT_FOOT_INDEX: (240, 945, -30),
}

# A person standing side-on, facing the right of the image (so the right side faces the camera).
SIDE_STANDING: dict[LM, tuple[float, float, float]] = {
    LM.NOSE: (345, 130, -100),
    LM.LEFT_EYE: (330, 115, 40),
    LM.RIGHT_EYE: (330, 115, -120),
    LM.LEFT_EAR: (300, 120, 150),
    LM.RIGHT_EAR: (300, 120, -150),
    LM.LEFT_SHOULDER: (300, 240, 200),
    LM.RIGHT_SHOULDER: (300, 240, -200),
    LM.LEFT_ELBOW: (300, 390, 200),
    LM.RIGHT_ELBOW: (300, 390, -200),
    LM.LEFT_WRIST: (310, 520, 200),
    LM.RIGHT_WRIST: (310, 520, -200),
    LM.LEFT_HIP: (300, 530, 150),
    LM.RIGHT_HIP: (300, 530, -150),
    LM.LEFT_KNEE: (302, 720, 150),
    LM.RIGHT_KNEE: (302, 720, -150),
    LM.LEFT_ANKLE: (300, 900, 150),
    LM.RIGHT_ANKLE: (300, 900, -150),
    LM.LEFT_HEEL: (290, 925, 150),
    LM.RIGHT_HEEL: (290, 925, -150),
    LM.LEFT_FOOT_INDEX: (350, 945, 150),
    LM.RIGHT_FOOT_INDEX: (350, 945, -150),
}


def make_pose(
    points: dict[LM, tuple[float, float, float]],
    overrides: dict[LM, tuple[float, float, float]] | None = None,
    confidence: float = 0.95,
    low_confidence: set[LM] | None = None,
    width: int = WIDTH,
    height: int = HEIGHT,
) -> Pose:
    merged = {**points, **(overrides or {})}
    landmarks = []
    for index in range(NUM_LANDMARKS):
        x, y, z = merged.get(index, (width / 2, height / 2, 0.0))
        conf = 0.1 if low_confidence and index in low_confidence else confidence
        landmarks.append(
            Landmark(
                x=x,
                y=y,
                z=z,
                visibility=conf,
                presence=conf,
                in_frame=(-0.02 * width <= x <= 1.02 * width and -0.02 * height <= y <= 1.02 * height),
            )
        )
    return Pose(landmarks=tuple(landmarks), image_width=width, image_height=height)


def _swap_side(lm: LM) -> LM:
    if lm.name.startswith("LEFT_"):
        return LM[lm.name.replace("LEFT_", "RIGHT_", 1)]
    if lm.name.startswith("RIGHT_"):
        return LM[lm.name.replace("RIGHT_", "LEFT_", 1)]
    return lm


def mirror(points: dict[LM, tuple[float, float, float]]) -> dict[LM, tuple[float, float, float]]:
    """The physically mirrored person: flipped horizontally with left/right body sides swapped
    (a side-view person facing right with the right side to the camera becomes one facing left
    with the left side to the camera)."""
    return {_swap_side(lm): (WIDTH - x, y, z) for lm, (x, y, z) in points.items()}
