from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    from .settings import (
        DATABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
        SUPABASE_STORAGE_BUCKET,
        SUPABASE_URL,
        UPLOAD_DIR,
    )
except ImportError:
    from settings import DATABASE_URL
    from settings import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_STORAGE_BUCKET, SUPABASE_URL, UPLOAD_DIR


class StorageError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


def _supabase_config() -> tuple[str, str, str] | None:
    if not SUPABASE_URL and not SUPABASE_SERVICE_ROLE_KEY:
        return None
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise StorageError("Configure both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    if not SUPABASE_STORAGE_BUCKET:
        raise StorageError("SUPABASE_STORAGE_BUCKET cannot be empty.")
    return SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_STORAGE_BUCKET


def validate_storage_configuration() -> None:
    config = _supabase_config()
    uses_postgres = DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+"))
    if uses_postgres and config is None:
        raise StorageError("Configure Supabase Storage when using a hosted database.")


def store_report_photo(filename: str, content: bytes, content_type: str) -> None:
    config = _supabase_config()
    if config is None:
        try:
            (UPLOAD_DIR / filename).write_bytes(content)
        except OSError as exc:
            raise StorageError("Local image storage is unavailable.") from exc
        return

    base_url, service_key, bucket = config
    object_path = f"{quote(bucket, safe='')}/{quote(filename, safe='')}"
    request = Request(
        f"{base_url}/storage/v1/object/{object_path}",
        data=content,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            response.read()
    except HTTPError as exc:
        raise StorageError(f"Supabase Storage upload returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise StorageError("Supabase Storage could not be reached.") from exc


def read_report_photo(filename: str) -> tuple[bytes, str]:
    config = _supabase_config()
    if config is None:
        path = Path(UPLOAD_DIR) / filename
        try:
            return path.read_bytes(), mimetypes.guess_type(filename)[0] or "application/octet-stream"
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise StorageError("Local image storage is unavailable.") from exc

    base_url, service_key, bucket = config
    object_path = f"{quote(bucket, safe='')}/{quote(filename, safe='')}"
    request = Request(
        f"{base_url}/storage/v1/object/{object_path}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            content = response.read()
            content_type = response.headers.get_content_type()
        return content, content_type
    except HTTPError as exc:
        if exc.code == 404:
            raise StorageError("Image file is unavailable.", status_code=404) from exc
        raise StorageError(f"Supabase Storage download returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise StorageError("Supabase Storage could not be reached.") from exc
