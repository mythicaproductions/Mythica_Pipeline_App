"""Image storage — turns raw bytes into a URL the caller can display.

Why this exists: OpenAI returns raw image bytes, not a link. To show an image in
ClickUp it must be hosted at a reachable URL first (see CLAUDE.md §2).

Backends (choose via STORAGE_BACKEND env var):
  - "datauri" (default): dev-only inline data: URI. Fine for local testing and
    Claude Desktop, but NOT reachable by ClickUp Brain.
  - "server": the MCP server hosts the image itself at /images/<id>.png. Once the
    server is deployed with a public address (PUBLIC_BASE_URL), these links are
    reachable by ClickUp. Ephemeral (in-memory) — the fast path to ClickUp.
  - "clickup": upload the image to ClickUp as a task attachment and return the
    ClickUp-hosted URL. Durable (lives in ClickUp storage). Needs
    CLICKUP_API_TOKEN and a task id (CLICKUP_DEFAULT_TASK_ID or per-call task_id).
  - "r2" / "s3": durable public bucket. Best long-term; not implemented yet.

Backends accept optional per-call keyword opts (e.g. task_id); backends that
don't use them ignore them.
"""
from __future__ import annotations

import base64
import os
import uuid


class Storage:
    def save(self, data: bytes, content_type: str = "image/png", **opts) -> str:
        raise NotImplementedError


class DataUriStorage(Storage):
    """Dev-only. Returns an inline data: URI. Not reachable by ClickUp."""

    def save(self, data: bytes, content_type: str = "image/png", **opts) -> str:
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{content_type};base64,{b64}"


# --- Server-hosted store (fast path: no external bucket needed) --------------
# The MCP server is already a web server, so it hosts generated images at its own
# public URL. In-memory and ephemeral (cleared on restart) — fine for a first
# ClickUp-facing version; swap for R2/S3 later for durability. Note: assumes a
# single server process (Railway default); multiple workers would each have a
# separate store.
_IMAGE_STORE: dict[str, tuple[bytes, str]] = {}
_STORE_ORDER: list[str] = []
_STORE_MAX = 200


def put_image(data: bytes, content_type: str = "image/png") -> str:
    image_id = uuid.uuid4().hex
    _IMAGE_STORE[image_id] = (data, content_type)
    _STORE_ORDER.append(image_id)
    while len(_STORE_ORDER) > _STORE_MAX:
        _IMAGE_STORE.pop(_STORE_ORDER.pop(0), None)
    return image_id


def get_image(image_id: str) -> tuple[bytes, str] | None:
    return _IMAGE_STORE.get(image_id)


def _public_base_url() -> str:
    """The server's public address, for building image URLs.

    Prefers an explicit PUBLIC_BASE_URL, then auto-detects common hosts so no
    manual setup is needed after deploy. Falls back to localhost for dev.
    """
    explicit = os.environ.get("PUBLIC_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    railway = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if railway:
        return f"https://{railway}"
    fly = os.environ.get("FLY_APP_NAME")
    if fly:
        return f"https://{fly}.fly.dev"
    return "http://localhost:8000"


class ServerStorage(Storage):
    """Host the image on this server at /images/<id>.png.

    PUBLIC_BASE_URL must be the server's public address once deployed
    (e.g. https://mythica-mcp.up.railway.app). Defaults to localhost for dev.
    """

    def save(self, data: bytes, content_type: str = "image/png", **opts) -> str:
        image_id = put_image(data, content_type)
        return f"{_public_base_url()}/images/{image_id}.png"


class ClickUpStorage(Storage):
    """Upload the image to ClickUp as a task attachment; return its URL.

    The image lands in ClickUp storage permanently. Config:
      - CLICKUP_API_TOKEN: personal API token (Settings -> Apps -> API Token).
      - task id: per-call `task_id` opt, else CLICKUP_DEFAULT_TASK_ID.
    """

    def save(self, data: bytes, content_type: str = "image/png", **opts) -> str:
        import requests  # lazy: only needed for this backend

        token = os.environ.get("CLICKUP_API_TOKEN")
        if not token:
            raise RuntimeError("CLICKUP_API_TOKEN is not set in the environment")
        task_id = opts.get("task_id") or os.environ.get("CLICKUP_DEFAULT_TASK_ID")
        if not task_id:
            raise RuntimeError(
                "No ClickUp task id (set CLICKUP_DEFAULT_TASK_ID or pass task_id)"
            )

        ext = "png" if "png" in content_type else "jpg"
        filename = f"mythica_{uuid.uuid4().hex}.{ext}"
        resp = requests.post(
            f"https://api.clickup.com/api/v2/task/{task_id}/attachment",
            headers={"Authorization": token},
            files={"attachment": (filename, data, content_type)},
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
        url = body.get("url") or body.get("url_w_host") or body.get("url_w_query")
        if not url:
            raise RuntimeError(f"ClickUp attachment response had no url: {body}")
        return url


class BucketStorage(Storage):
    """TODO: Cloudflare R2 / S3 for durable storage. Needs bucket + credentials."""

    def save(self, data: bytes, content_type: str = "image/png", **opts) -> str:
        raise NotImplementedError(
            "Bucket storage is not configured yet (see CLAUDE.md §9)."
        )


def get_storage() -> Storage:
    backend = os.environ.get("STORAGE_BACKEND", "datauri").lower()
    if backend == "datauri":
        return DataUriStorage()
    if backend == "server":
        return ServerStorage()
    if backend == "clickup":
        return ClickUpStorage()
    if backend in ("r2", "s3", "bucket"):
        return BucketStorage()
    raise ValueError(f"Unknown STORAGE_BACKEND '{backend}'")
