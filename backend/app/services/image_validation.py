"""Validates uploaded images and produces a sanitised copy (re-encoded JPEG without EXIF/GPS metadata)."""

import hashlib
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import PayloadTooLargeError, UnsupportedMediaError, ValidationFailedError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_STORED_SIDE_PX = 4096
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ValidatedImage:
    image: Image.Image  # RGB, orientation applied
    jpeg_bytes: bytes
    sha256: str

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height


async def read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    buffer = bytearray()
    while chunk := await upload.read(CHUNK_SIZE):
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise PayloadTooLargeError(f"The image is larger than {max_bytes // (1024 * 1024)} MB.")
    return bytes(buffer)


def validate_image(data: bytes, filename: str | None, content_type: str | None, max_pixels: int) -> ValidatedImage:
    extension = PurePath(filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedMediaError("Only JPEG, PNG or WebP images are accepted.")
    if (content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaError("Only JPEG, PNG or WebP images are accepted.")
    if not data:
        raise ValidationFailedError("The uploaded file is empty.")

    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise UnsupportedMediaError("The file content is not a JPEG, PNG or WebP image.")
            width, height = probe.size
            if width * height > max_pixels:
                raise ValidationFailedError("The image dimensions are too large.")
            probe.verify()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnsupportedMediaError, ValidationFailedError):
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
    ) as exc:
        raise ValidationFailedError("The image could not be read. It may be corrupted or incomplete.") from exc

    if max(image.size) > MAX_STORED_SIDE_PX:
        image.thumbnail((MAX_STORED_SIDE_PX, MAX_STORED_SIDE_PX), Image.Resampling.LANCZOS)

    out = BytesIO()
    image.save(out, format="JPEG", quality=92)  # no exif argument: metadata (including GPS) is dropped
    jpeg = out.getvalue()
    return ValidatedImage(image=image, jpeg_bytes=jpeg, sha256=hashlib.sha256(jpeg).hexdigest())
