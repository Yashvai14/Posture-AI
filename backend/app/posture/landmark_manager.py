"""Landmark manager for extracting, querying, and navigating MediaPipe pose landmarks."""

from dataclasses import dataclass
from typing import Sequence

from app.posture.geometry import Point, distance, midpoint
from app.posture.landmarks import LM, Landmark, Pose, View, side_landmarks
from app.posture.thresholds import MIN_LANDMARK_CONFIDENCE


@dataclass(frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def center(self) -> Point:
        return ((self.left + self.right) / 2.0, (self.top + self.bottom) / 2.0)


class LandmarkManager:
    """Provides high-level queries and validations over detected pose landmarks."""

    def __init__(self, pose: Pose):
        self.pose = pose

    def get(self, lm: LM) -> Landmark:
        return self.pose[lm]

    def point(self, lm: LM) -> Point:
        return self.pose[lm].xy

    def is_visible(self, lm: LM, min_confidence: float = MIN_LANDMARK_CONFIDENCE) -> bool:
        p = self.pose[lm]
        return bool(p.in_frame and p.confidence >= min_confidence)

    def all_visible(self, *landmarks: LM, min_confidence: float = MIN_LANDMARK_CONFIDENCE) -> bool:
        return all(self.is_visible(lm, min_confidence) for lm in landmarks)

    def any_visible(self, *landmarks: LM, min_confidence: float = MIN_LANDMARK_CONFIDENCE) -> bool:
        return any(self.is_visible(lm, min_confidence) for lm in landmarks)

    def confidence_of(self, *landmarks: LM) -> float:
        """Returns the minimum confidence among specified landmarks."""
        if not landmarks:
            return 0.0
        return min(self.pose[lm].confidence for lm in landmarks)

    def midpoint_of(self, a: LM, b: LM) -> Point:
        return midpoint(self.point(a), self.point(b))

    def distance_between(self, a: LM, b: LM) -> float:
        return distance(self.point(a), self.point(b))

    def bounding_box(self, landmarks: Sequence[LM] | None = None) -> BoundingBox:
        lms = [self.pose[lm] for lm in landmarks] if landmarks else [lm for lm in self.pose.landmarks if lm.in_frame]
        if not lms:
            return BoundingBox(0.0, 0.0, 0.0, 0.0)
        xs = [p.x for p in lms]
        ys = [p.y for p in lms]
        return BoundingBox(left=min(xs), top=min(ys), right=max(xs), bottom=max(ys))

    def side_keys(self, view: View) -> dict[str, LM]:
        side = "left" if view == View.LEFT_SIDE else "right"
        return side_landmarks(side)
