import enum
from dataclasses import dataclass


class LM(enum.IntEnum):
    """MediaPipe BlazePose landmark indices used by the pipeline."""

    NOSE = 0
    LEFT_EYE = 2
    RIGHT_EYE = 5
    LEFT_EAR = 7
    RIGHT_EAR = 8
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


NUM_LANDMARKS = 33

# Landmarks the body-level checks and metrics depend on.
BODY_PAIRS: tuple[tuple[LM, LM], ...] = (
    (LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER),
    (LM.LEFT_HIP, LM.RIGHT_HIP),
    (LM.LEFT_KNEE, LM.RIGHT_KNEE),
    (LM.LEFT_ANKLE, LM.RIGHT_ANKLE),
)

SKELETON: tuple[tuple[LM, LM], ...] = (
    (LM.LEFT_EAR, LM.LEFT_EYE),
    (LM.RIGHT_EAR, LM.RIGHT_EYE),
    (LM.LEFT_EYE, LM.NOSE),
    (LM.RIGHT_EYE, LM.NOSE),
    (LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER),
    (LM.LEFT_SHOULDER, LM.LEFT_ELBOW),
    (LM.LEFT_ELBOW, LM.LEFT_WRIST),
    (LM.RIGHT_SHOULDER, LM.RIGHT_ELBOW),
    (LM.RIGHT_ELBOW, LM.RIGHT_WRIST),
    (LM.LEFT_SHOULDER, LM.LEFT_HIP),
    (LM.RIGHT_SHOULDER, LM.RIGHT_HIP),
    (LM.LEFT_HIP, LM.RIGHT_HIP),
    (LM.LEFT_HIP, LM.LEFT_KNEE),
    (LM.LEFT_KNEE, LM.LEFT_ANKLE),
    (LM.RIGHT_HIP, LM.RIGHT_KNEE),
    (LM.RIGHT_KNEE, LM.RIGHT_ANKLE),
    (LM.LEFT_ANKLE, LM.LEFT_HEEL),
    (LM.LEFT_HEEL, LM.LEFT_FOOT_INDEX),
    (LM.RIGHT_ANKLE, LM.RIGHT_HEEL),
    (LM.RIGHT_HEEL, LM.RIGHT_FOOT_INDEX),
)


class View(enum.StrEnum):
    FRONT = "front"
    BACK = "back"
    LEFT_SIDE = "left_side"  # the person's left side faces the camera
    RIGHT_SIDE = "right_side"

    @property
    def is_side(self) -> bool:
        return self in (View.LEFT_SIDE, View.RIGHT_SIDE)


@dataclass(frozen=True)
class Landmark:
    x: float  # pixels, left → right
    y: float  # pixels, top → bottom
    z: float  # relative depth in pixel scale; smaller is closer to the camera
    visibility: float
    presence: float
    in_frame: bool

    @property
    def confidence(self) -> float:
        return min(self.visibility, self.presence)

    @property
    def xy(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class Pose:
    landmarks: tuple[Landmark, ...]
    image_width: int
    image_height: int

    def __post_init__(self) -> None:
        if len(self.landmarks) != NUM_LANDMARKS:
            raise ValueError(f"expected {NUM_LANDMARKS} landmarks, got {len(self.landmarks)}")

    def __getitem__(self, index: LM) -> Landmark:
        return self.landmarks[index]


def side_landmarks(side: str) -> dict[str, LM]:
    """Landmarks for one body side ('left' or 'right')."""
    prefix = side.upper()
    return {name: LM[f"{prefix}_{name.upper()}"] for name in ("ear", "shoulder", "hip", "knee", "ankle")}
