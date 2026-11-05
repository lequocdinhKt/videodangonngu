"""Upload, approve and publish generated demo assets through the real admin API."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "demo_assets"
API_ORIGIN = os.getenv("DEMO_API_URL", "http://localhost:8000").rstrip("/")


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing environment variable: {name}")
    return value


def upload(client: httpx.Client, token: str, video_id: str, kind: str, path: Path, language_code: str | None = None):
    headers = {"Authorization": f"Bearer {token}"}
    content_type = "video/mp4" if kind == "video" else "image/webp" if kind == "thumbnail" else "application/x-subrip"
    request = client.post(
        f"/api/admin/videos/{video_id}/upload-url",
        headers=headers,
        json={"kind": kind, "filename": path.name, "content_type": content_type, "size_bytes": path.stat().st_size, "language_code": language_code},
    )
    request.raise_for_status()
    signed = request.json()
    if signed.get("upload_url"):
        with path.open("rb") as stream:
            result = httpx.put(signed["upload_url"], headers=signed["headers"], content=stream, timeout=180)
        result.raise_for_status()
    else:
        with path.open("rb") as stream:
            result = client.post(signed["fallback_url"], headers=headers, files={"file": (path.name, stream, content_type)})
        result.raise_for_status()
    complete = client.post(
        f"/api/admin/videos/{video_id}/assets/complete",
        headers=headers,
        json={"kind": kind, "key": signed["key"], "language_code": language_code},
    )
    complete.raise_for_status()


def main():
    manifest_path = ASSETS / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("Run: python demo/generate_demo_assets.py")
    with httpx.Client(base_url=API_ORIGIN, timeout=90) as client:
        login = client.post("/api/admin/auth/login", json={"email": require("DEMO_ADMIN_EMAIL"), "password": require("DEMO_ADMIN_PASSWORD")})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        for demo in json.loads(manifest_path.read_text(encoding="utf-8")):
            draft = client.post("/api/admin/videos/draft", headers=headers, json={"translations": demo["translations"]})
            draft.raise_for_status()
            video_id = draft.json()["id"]
            upload(client, token, video_id, "video", ASSETS / demo["video"])
            upload(client, token, video_id, "thumbnail", ASSETS / demo["thumbnail"])
            for language_code, relative_path in demo["srt_subtitles"].items():
                upload(client, token, video_id, "subtitle", ASSETS / relative_path, language_code)
                if language_code != "vi-VN":
                    track = client.get(f"/api/admin/videos/{video_id}/subtitles/{language_code}", headers=headers)
                    track.raise_for_status()
                    approve = client.put(
                        f"/api/admin/videos/{video_id}/subtitles/{language_code}",
                        headers=headers,
                        json={"cues": track.json()["cues"], "approved": True},
                    )
                    approve.raise_for_status()
            publish = client.post(f"/api/admin/videos/{video_id}/publish", headers=headers)
            publish.raise_for_status()
            print(f"Published {demo['slug']} ({video_id})")


if __name__ == "__main__":
    main()
