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


@mcp.tool
def generate_image(
    prompt: str,
    style: str = "",
    size: str = "1024x1024",
    provider: str = "openai",
) -> dict:
    """Generate an image from a text prompt and return its URL + metadata.

    Args:
        prompt: What to generate.
        style: Optional style template name (see list_style_templates). Empty = none.
        size: Image size, e.g. "1024x1024".
        provider: Which image generator to use (default "openai").
    """
    prefix = get_template(style) if style else ""
    full_prompt = f"{prefix}, {prompt}" if prefix else prompt

    image_bytes = get_provider(provider).generate(full_prompt, size)
    url = get_storage().save(image_bytes, content_type="image/png")

    record = {
        "url": url,
        "prompt": prompt,
        "style": style or None,
        "provider": provider,
        "size": size,
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
app = mcp.http_app(path="/mcp")
app.add_middleware(ApiKeyMiddleware)
app.router.routes.append(Route("/images/{name}", serve_image, methods=["GET"]))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
