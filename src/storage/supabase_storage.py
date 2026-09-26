import json
import os
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


STORAGE_PREFIX = "supabase://"


class SupabaseStorageError(RuntimeError):
    """Raised when a private Supabase Storage operation fails."""


class SupabaseStorage:
    def __init__(self, url=None, service_role_key=None, bucket=None):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.service_role_key = service_role_key or os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY", ""
        )
        self.bucket = bucket or os.getenv("SUPABASE_CAMERA_BUCKET", "camera-videos")

    @property
    def configured(self):
        return bool(self.url and self.service_role_key and self.bucket)

    def require_configured(self):
        if not self.configured:
            raise SupabaseStorageError(
                "Supabase Storage is not configured. Set SUPABASE_URL, "
                "SUPABASE_SERVICE_ROLE_KEY and SUPABASE_CAMERA_BUCKET."
            )

    @staticmethod
    def object_source(bucket, object_path):
        return f"{STORAGE_PREFIX}{bucket}/{object_path}"

    @staticmethod
    def is_storage_source(source):
        return str(source or "").startswith(STORAGE_PREFIX)

    def parse_source(self, source):
        value = str(source or "")
        if not self.is_storage_source(value):
            raise SupabaseStorageError(f"Not a Supabase Storage source: {source}")
        parts = value[len(STORAGE_PREFIX):].split("/", 1)
        if len(parts) != 2 or not all(parts):
            raise SupabaseStorageError(f"Invalid Supabase Storage source: {source}")
        return parts[0], parts[1]

    @staticmethod
    def safe_object_path(camera_id, filename):
        camera_part = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(camera_id)).strip("._")
        filename_part = Path(filename).name
        stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename_part).stem).strip("._")
        suffix = Path(filename_part).suffix.lower()
        return f"{camera_part or 'camera'}/{stem or 'video'}{suffix}"

    def _request(self, method, path, body=None, content_type=None, extra_headers=None):
        self.require_configured()
        endpoint = f"{self.url}/storage/v1/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)
        try:
            with urlopen(
                Request(endpoint, data=body, headers=headers, method=method),
                timeout=120,
            ) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            detail = str(exc)
            if isinstance(exc, HTTPError):
                try:
                    detail = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
            raise SupabaseStorageError(detail) from exc

    def upload_file(self, camera_id, filename, content, content_type):
        object_path = self.safe_object_path(camera_id, filename)
        encoded = "/".join(quote(part, safe="") for part in object_path.split("/"))
        self._request(
            "POST",
            f"object/{quote(self.bucket, safe='')}/{encoded}",
            body=content,
            content_type=content_type,
            extra_headers={"x-upsert": "true"},
        )
        return self.object_source(self.bucket, object_path)

    def download_to_temp(self, source, camera_id):
        bucket, object_path = self.parse_source(source)
        encoded = "/".join(quote(part, safe="") for part in object_path.split("/"))
        content = self._request(
            "GET", f"object/{quote(bucket, safe='')}/{encoded}"
        )
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"crowd-camera-{camera_id}-",
            suffix=Path(object_path).suffix.lower() or ".video",
            delete=False,
        )
        try:
            temp_file.write(content)
            temp_file.close()
        except Exception:
            temp_file.close()
            Path(temp_file.name).unlink(missing_ok=True)
            raise
        return Path(temp_file.name)

    def exists(self, source):
        bucket, object_path = self.parse_source(source)
        encoded = "/".join(quote(part, safe="") for part in object_path.split("/"))
        try:
            self._request("HEAD", f"object/{quote(bucket, safe='')}/{encoded}")
            return True
        except SupabaseStorageError:
            return False

    def delete(self, source):
        bucket, object_path = self.parse_source(source)
        body = json.dumps(
            {"bucketId": bucket, "prefixes": [object_path]}
        ).encode("utf-8")
        self._request(
            "POST",
            "object/remove",
            body=body,
            content_type="application/json",
        )
