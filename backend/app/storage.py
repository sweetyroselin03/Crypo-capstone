import os
from pathlib import Path
from typing import Optional

class StorageBackend:
    """Storage interface for persistent encrypted file storage."""
    def save(self, key: str, data: bytes) -> str:
        raise NotImplementedError

    def get(self, key: str) -> Optional[bytes]:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        # Sanitize key to prevent path traversal
        safe_key = os.path.basename(key)
        return self.base_dir / safe_key

    def save(self, key: str, data: bytes) -> str:
        file_path = self._get_path(key)
        with open(file_path, "wb") as f:
            f.write(data)
        return str(file_path)

    def get(self, key: str) -> Optional[bytes]:
        file_path = self._get_path(key)
        if not file_path.exists():
            return None
        with open(file_path, "rb") as f:
            return f.read()

    def delete(self, key: str) -> bool:
        file_path = self._get_path(key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False


def get_storage() -> StorageBackend:
    from app.config import Config
    # If S3 credentials are provided, S3 storage can be used. Otherwise default to local.
    s3_bucket = os.environ.get("S3_BUCKET")
    if Config.STORAGE_TYPE == "s3" and s3_bucket:
        # Cloud S3-compatible fallback placeholder
        pass
    return LocalStorageBackend(Config.LOCAL_STORAGE_DIR)
