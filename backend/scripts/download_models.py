"""Downloads the MediaPipe Pose Landmarker model and verifies its checksum.

Usage (from the backend directory): python scripts/download_models.py
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/"
    "pose_landmarker_full.task"
)
MODEL_SHA256 = "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"
TARGET = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_full.task"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if TARGET.is_file() and sha256(TARGET) == MODEL_SHA256:
        print(f"Model already present: {TARGET}")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    partial = TARGET.with_suffix(".part")
    print(f"Downloading {MODEL_URL}")
    urllib.request.urlretrieve(MODEL_URL, partial)  # noqa: S310 (fixed https URL)
    digest = sha256(partial)
    if digest != MODEL_SHA256:
        partial.unlink()
        print(f"Checksum mismatch: expected {MODEL_SHA256}, got {digest}", file=sys.stderr)
        return 1
    partial.replace(TARGET)
    print(f"Saved {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
