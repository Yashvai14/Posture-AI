import threading
from pathlib import Path
from typing import Protocol

import numpy as np

from app.posture.landmarks import Landmark, Pose

FRAME_MARGIN = 0.02  # normalised; landmarks slightly outside the edge still count as in frame


class PoseDetector(Protocol):
    model_name: str

    def detect(self, rgb: np.ndarray) -> list[Pose]: ...


class MediaPipePoseDetector:
    """MediaPipe Pose Landmarker (BlazePose, 33 landmarks), image mode, CPU.

    Detects up to two people so that group photos can be rejected instead of silently analysing one person.
    The underlying landmarker is not thread-safe, so calls are serialised.
    """

    def __init__(self, model_path: Path, min_detection_confidence: float = 0.5, min_presence_confidence: float = 0.5):
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Pose model not found at {model_path}. "
                "Run `python scripts/download_models.py` in the backend directory."
            )
        self.model_path = model_path
        self.model_name = f"mediapipe-pose-landmarker:{model_path.stem}"
        self._min_detection = min_detection_confidence
        self._min_presence = min_presence_confidence
        self._landmarker = None
        self._lock = threading.Lock()

    def _get_landmarker(self):
        if self._landmarker is None:
            from mediapipe.tasks.python import BaseOptions, vision

            options = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=2,
                min_pose_detection_confidence=self._min_detection,
                min_pose_presence_confidence=self._min_presence,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
        return self._landmarker

    def close(self) -> None:
        """Releases the native landmarker; its worker threads otherwise keep the process alive at exit."""
        with self._lock:
            if self._landmarker is not None:
                self._landmarker.close()
                self._landmarker = None

    def detect(self, rgb: np.ndarray) -> list[Pose]:
        import mediapipe as mp

        height, width = rgb.shape[:2]
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb, dtype=np.uint8))
        with self._lock:
            result = self._get_landmarker().detect(image)
        return [self._to_pose(raw, width, height) for raw in result.pose_landmarks]

    @staticmethod
    def _to_pose(raw_landmarks, width: int, height: int) -> Pose:
        landmarks = tuple(
            Landmark(
                x=lm.x * width,
                y=lm.y * height,
                z=lm.z * width,
                visibility=float(lm.visibility or 0.0),
                presence=float(lm.presence or 0.0),
                in_frame=(-FRAME_MARGIN <= lm.x <= 1 + FRAME_MARGIN and -FRAME_MARGIN <= lm.y <= 1 + FRAME_MARGIN),
            )
            for lm in raw_landmarks
        )
        return Pose(landmarks=landmarks, image_width=width, image_height=height)
