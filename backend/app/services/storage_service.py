from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import Settings


class StorageService:
    """Object-storage adapter with a local fallback.

    Supabase is accessed through its documented Storage REST endpoints so the
    backend does not expose the service-role key to the browser.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return (
            self.settings.storage_backend == "supabase"
            and bool(self.settings.supabase_url)
            and bool(self.settings.supabase_service_role_key)
        )

    def _headers(self, mime_type: str | None = None) -> dict[str, str]:
        key = self.settings.supabase_service_role_key or ""
        headers = {"Authorization": f"Bearer {key}", "apikey": key}
        if mime_type:
            headers["Content-Type"] = mime_type
        return headers

    def upload(self, source: Path, object_key: str, mime_type: str) -> None:
        if not self.enabled:
            return
        endpoint = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.settings.supabase_storage_bucket}/{quote(object_key, safe='/')}"
        with source.open("rb") as handle, httpx.Client(timeout=90.0) as client:
            response = client.post(endpoint, headers={**self._headers(mime_type), "x-upsert": "true"}, content=handle.read())
        response.raise_for_status()

    def download(self, object_key: str, destination: Path) -> None:
        if not self.enabled:
            raise FileNotFoundError(destination)
        endpoint = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.settings.supabase_storage_bucket}/{quote(object_key, safe='/')}"
        with httpx.Client(timeout=90.0) as client:
            response = client.get(endpoint, headers=self._headers())
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)

    def public_url(self, object_key: str) -> str | None:
        if not self.enabled:
            return None
        return f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/public/{self.settings.supabase_storage_bucket}/{quote(object_key, safe='/')}"
