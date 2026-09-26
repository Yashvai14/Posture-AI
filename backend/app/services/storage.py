"""Private file storage. Files are only reachable through authorised API endpoints, never as static files."""

import os
import re
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

_KEY_PATTERN = re.compile(r"^(originals|annotated|reports)/[0-9a-f]{32}\.(jpg|pdf)$")


class PrivateStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, category: str, data: bytes, suffix: str) -> str:
        key = f"{category}/{uuid.uuid4().hex}{suffix}"
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temporary file first so readers never see a partial file.
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".part")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return key

    def path(self, key: str) -> Path:
        if not _KEY_PATTERN.match(key):
            raise ValueError(f"invalid storage key: {key!r}")
        return self.root / key

    def exists(self, key: str | None) -> bool:
        return bool(key) and self.path(key).is_file()

    def read(self, key: str) -> bytes:
        return self.path(key).read_bytes()

    def delete(self, key: str | None) -> None:
        if key:
            self.path(key).unlink(missing_ok=True)


@lru_cache
def get_storage() -> PrivateStorage:
    return PrivateStorage(get_settings().STORAGE_DIR)
