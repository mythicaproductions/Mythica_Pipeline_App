"""Mythica MCP server — exposes image generation over Streamable HTTP.

Second doorway onto the shared engine (the first is the Tkinter desktop app).
The desktop GUI is NOT touched by this file. See CLAUDE.md for the full design.

Run locally:
    OPENAI_API_KEY=sk-...  python src/mcp_server.py
Deploy (Railway/Fly, via Dockerfile/Procfile):
    uvicorn mcp_server:app --app-dir src --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import datetime
import os
import sys

# Treat src/ as the import root (same convention as main.py) so this runs both
# directly (python src/mcp_server.py) and via uvicorn --app-dir src.
_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from integrations.storage import get_image, get_storage
from integrations.style_templates import get_template, list_templates
from providers import available_providers, get_provider

mcp = FastMCP("Mythica Image Pipeline")

# In-memory, per-process history. Simple on purpose for now — revisit for a
# durable store later (see CLAUDE.md §9).
_RECENT: list[dict] = []
_RECENT_MAX = 50


# Named aspect ratios -> gpt-image sizes (explicit "WxH" also accepted).
_ASPECTS = {
    "square": "1024x1024",
    "portrait": "1024x1536",
    "tall": "1024x1536",
    "landscape": "1536x1024",
    "wide": "1536x1024",
}
_MAX_COUNT = 6


def _resolve_size(size: str) -> str:
    return _ASPECTS.get(size.strip().lower(), size.strip())


def _resolve_style(style: str) -> str:
    """A known template name expands to its saved prefix; anything else is used
    verbatim as freeform style text (so styles can be pasted straight through)."""
    if not style:
        return ""
    try:
        return get_template(style)
    except ValueError:
        return style


@mcp.tool
def generate_image(
    prompt: str,
    style: str = "",
    size: str = "square",
    provider: str = "openai",
    count: int = 1,
    task_id: str = "",
) -> dict:
    """Generate one or more images from a text prompt.

    Args:
        prompt: What to generate. You can bake style language right into this.
        style: Optional. A saved template name (see list_style_templates) OR any
            freeform style text pasted directly (e.g. "cinematic, moody lighting").
        size: "square", "portrait"/"tall", "landscape"/"wide", or explicit "WxH"
            like "1024x1024".
        provider: Which image generator to use (default "openai").
        count: How many images to generate, 1-6.
        task_id: Optional. With the ClickUp storage backend, attach the image(s)
            to this ClickUp task instead of the default library task.
    """
    count = max(1, min(int(count), _MAX_COUNT))
    px = _resolve_size(size)
    prefix = _resolve_style(style)
    full_prompt = f"{prefix}, {prompt}" if prefix else prompt

    gen = get_provider(provider)
    storage = get_storage()
    urls = [
        storage.save(
            gen.generate(full_prompt, px),
            content_type="image/png",
            task_id=task_id or None,
        )
        for _ in range(count)
    ]

    record = {
        "url": urls[0],          # first image (kept for simple inline rendering)
        "images": urls,          # all generated image URLs
        "count": len(urls),
        "prompt": prompt,
        "style": style or None,
        "size": px,
        "provider": provider,
        "task_id": task_id or None,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _RECENT.insert(0, record)
    del _RECENT[_RECENT_MAX:]
    return record


@mcp.tool
def list_style_templates() -> list:
    """List available style templates that can be passed as `style`."""
    return list_templates()


@mcp.tool
def list_recent_generations(n: int = 10) -> list:
    """Return the most recent generations from this server session (in-memory)."""
    return _RECENT[: max(0, n)]


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Reject calls without the shared API key. If MCP_API_KEY is unset, auth is
    disabled (dev mode) — set it in production so only your clients can call."""

    async def dispatch(self, request, call_next):
        # Hosted images must be publicly fetchable (ClickUp/browsers load them
        # without the API key). They're protected by unguessable capability URLs.
        if request.url.path.startswith("/images/"):
            return await call_next(request)
        expected = os.environ.get("MCP_API_KEY")
        if expected:
            provided = request.headers.get("x-api-key")
            if not provided:
                auth = request.headers.get("authorization", "").strip()
                # Accept "Authorization: Bearer <key>" or a raw "Authorization: <key>"
                # (clients differ on whether they prepend the Bearer scheme).
                if auth.lower().startswith("bearer "):
                    provided = auth[7:].strip()
                elif auth:
                    provided = auth
            if provided != expected:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


async def serve_image(request):
    """Publicly serve a hosted image by id (used by STORAGE_BACKEND=server)."""
    image_id = request.path_params["name"].rsplit(".", 1)[0]
    item = get_image(image_id)
    if item is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    data, content_type = item
    return Response(content=data, media_type=content_type)


# Streamable HTTP ASGI app. Verified booting on fastmcp 3.4.4.
# stateless_http + json_response: each request is self-contained (no MCP session
# id to track) and responses are plain JSON instead of SSE streams. This is much
# more compatible with connectors like ClickUp that don't manage MCP sessions —
# stateful/SSE mode caused ClickUp's connect to loop and hang.
app = mcp.http_app(path="/mcp", stateless_http=True, json_response=True)
app.add_middleware(ApiKeyMiddleware)
app.router.routes.append(Route("/images/{name}", serve_image, methods=["GET"]))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
