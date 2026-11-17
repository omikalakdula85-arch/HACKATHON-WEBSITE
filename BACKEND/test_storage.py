import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from . import storage
    from .database import normalize_database_url
except ImportError:
    import storage
    from database import normalize_database_url


class StorageTests(unittest.TestCase):
    def test_local_photo_storage_remains_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(storage, "UPLOAD_DIR", Path(temp_dir)),
                patch.object(storage, "SUPABASE_URL", ""),
                patch.object(storage, "SUPABASE_SERVICE_ROLE_KEY", ""),
            ):
                storage.store_report_photo("sample.png", b"\x89PNG\r\n\x1a\nimage", "image/png")
                contents, content_type = storage.read_report_photo("sample.png")

        self.assertEqual(contents, b"\x89PNG\r\n\x1a\nimage")
        self.assertEqual(content_type, "image/png")

    def test_supabase_photo_upload_uses_private_service_headers(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        with (
            patch.object(storage, "SUPABASE_URL", "https://project.supabase.co"),
            patch.object(storage, "SUPABASE_SERVICE_ROLE_KEY", "test-service-key"),
            patch.object(storage, "SUPABASE_STORAGE_BUCKET", "report-photos"),
            patch.object(storage, "urlopen", return_value=response) as urlopen,
        ):
            storage.store_report_photo("sample.png", b"png-data", "image/png")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://project.supabase.co/storage/v1/object/report-photos/sample.png")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-service-key")
        self.assertEqual(request.get_header("Content-type"), "image/png")
        self.assertEqual(request.data, b"png-data")

    def test_postgres_urls_use_psycopg_driver(self) -> None:
        self.assertEqual(
            normalize_database_url("postgresql://user:pass@db.example.test/app"),
            "postgresql+psycopg://user:pass@db.example.test/app",
        )
        self.assertEqual(normalize_database_url("sqlite:///local.db"), "sqlite:///local.db")


if __name__ == "__main__":
    unittest.main()
