"""Image preprocessing for posture analysis.

Handles EXIF orientation correction, dimension checks, aspect-ratio-preserving
resizing, and preliminary image quality metrics (brightness, contrast, sharpness).
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app.posture.thresholds import (
    BRIGHTNESS_RANGE,
    MAX_IMAGE_DIMENSION_PX,
    MIN_CONTRAST,
    MIN_SHARPNESS,
    MIN_SHORT_SIDE_PX,
)


@dataclass(frozen=True)
class PreprocessedImage:
    rgb: np.ndarray
    original_size: tuple[int, int]  # (width, height)
    processed_size: tuple[int, int]  # (width, height)
    scale_factor: float  # processed / original
    brightness: float
    contrast: float
    sharpness: float
    metadata: dict[str, Any]


def to_grayscale(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def laplacian_variance(gray: np.ndarray) -> float:
    """Computes blur via discrete 2D Laplacian variance."""
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    lap = -4.0 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return float(lap.var())


def preprocess_image(image_input: Image.Image | np.ndarray) -> PreprocessedImage:
    """Normalises orientation, checks size, scales if needed without distortion, and computes image stats."""
    if isinstance(image_input, np.ndarray):
        pil_img = Image.fromarray(image_input)
    else:
        pil_img = image_input

    # 1. EXIF Orientation correction (prevents upside down / rotated phone photos)
    try:
        pil_img = ImageOps.exif_transpose(pil_img) or pil_img
    except Exception:
        pass

    # Ensure 8-bit RGB
    pil_img = pil_img.convert("RGB")
    orig_w, orig_h = pil_img.size

    # 2. Proportion-preserving resize if exceeding maximum dimension
    max_dim = max(orig_w, orig_h)
    scale_factor = 1.0
    if max_dim > MAX_IMAGE_DIMENSION_PX:
        scale_factor = MAX_IMAGE_DIMENSION_PX / float(max_dim)
        new_w = max(1, int(round(orig_w * scale_factor)))
        new_h = max(1, int(round(orig_h * scale_factor)))
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    rgb = np.ascontiguousarray(np.asarray(pil_img), dtype=np.uint8)
    cur_h, cur_w = rgb.shape[:2]

    # 3. Image diagnostics (brightness, contrast, sharpness)
    gray = to_grayscale(rgb.astype(np.float32))
    brightness = float(gray.mean())
    contrast = float(gray.std())
    sharpness = laplacian_variance(gray)

    return PreprocessedImage(
        rgb=rgb,
        original_size=(orig_w, orig_h),
        processed_size=(cur_w, cur_h),
        scale_factor=scale_factor,
        brightness=brightness,
        contrast=contrast,
        sharpness=sharpness,
        metadata={
            "is_portrait": cur_h > cur_w,
            "aspect_ratio": round(cur_w / max(1, cur_h), 3),
            "brightness_ok": BRIGHTNESS_RANGE[0] <= brightness <= BRIGHTNESS_RANGE[1],
            "contrast_ok": contrast >= MIN_CONTRAST,
            "sharpness_ok": sharpness >= MIN_SHARPNESS,
            "resolution_ok": min(cur_w, cur_h) >= MIN_SHORT_SIDE_PX,
        },
    )
