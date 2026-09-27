"""Configured posture engine: one shared MediaPipe detector for the process."""

import threading

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.posture.detector import MediaPipePoseDetector
from app.posture.pipeline import PostureResult, analyze_image

_detector: MediaPipePoseDetector | None = None
_lock = threading.Lock()


def get_detector() -> MediaPipePoseDetector:
    global _detector
    with _lock:
        if _detector is None:
            _detector = MediaPipePoseDetector(get_settings().POSE_MODEL_PATH)
        return _detector


def analyze(image: Image.Image, allow_partial: bool = True) -> PostureResult:
    return analyze_image(np.asarray(image.convert("RGB")), get_detector(), allow_partial=allow_partial)


def shutdown() -> None:
    global _detector
    with _lock:
        if _detector is not None:
            _detector.close()
            _detector = None
