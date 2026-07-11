"""Notion REST API integration.

Supports:
  - Listing databases the token can access
  - Creating a new page in a database
  - Uploading an image to a page via the Notion File Upload beta API
"""

from __future__ import annotations

import requests

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def list_databases(token: str) -> list[dict]:
    resp = requests.post(
        f"{NOTION_API}/search",
        headers=_headers(token),
        json={"filter": {"value": "database", "property": "object"}, "page_size": 50},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def get_database_title(db: dict) -> str:
    try:
        parts = db.get("title", [])
        return "".join(p.get("plain_text", "") for p in parts) or "Untitled"
    except Exception:
        return db.get("id", "Unknown")[:8]


def _upload_image_to_notion(token: str, page_id: str, image_bytes: bytes) -> bool:
    """
    Attempt to upload image via Notion File Upload beta API.
    Returns True on success, False if the API is unavailable.
    """
    # Step 1: Initialize upload
    init_resp = requests.post(
        f"{NOTION_API}/file-uploads",
        headers=_headers(token),
        json={"name": "mythica_generated.png", "content_type": "image/png"},
        timeout=15,
    )
    if init_resp.status_code not in (200, 201):
        return False

    data = init_resp.json()
    upload_url = data.get("upload_url")
    file_id = data.get("id")
    if not upload_url or not file_id:
        return False

    # Step 2: Upload binary data
    put_resp = requests.put(
        upload_url,
        headers={"Content-Type": "image/png"},
        data=image_bytes,
        timeout=30,
    )
    if put_resp.status_code not in (200, 204):
        return False

    # Step 3: Append image block to page
    block_resp = requests.patch(
        f"{NOTION_API}/blocks/{page_id}/children",
        headers=_headers(token),
        json={
            "children": [
                {
                    "type": "image",
                    "image": {
                        "type": "file",
                        "file_upload": {"id": file_id},
                    },
                }
            ]
        },
        timeout=15,
    )
    return block_resp.status_code in (200, 201)


def _get_title_property_name(token: str, database_id: str) -> str:
    """Return the name of the title-type property in this database."""
    try:
        resp = requests.get(
            f"{NOTION_API}/databases/{database_id}",
            headers=_headers(token),
            timeout=15,
        )
        resp.raise_for_status()
        for name, prop in resp.json().get("properties", {}).items():
            if prop.get("type") == "title":
                return name
    except Exception:
        pass
    return "Name"  # safe fallback


def create_page_with_image(
    token: str,
    database_id: str,
    title: str,
    prompt: str,
    image_bytes: bytes,
) -> dict:
    """
    Create a new page in a Notion database, add the prompt as a text block,
    and attempt to attach the image. Returns info about what was created.
    """
    # Discover the title property name for this specific database
    title_prop = _get_title_property_name(token, database_id)

    # Create the page
    page_resp = requests.post(
        f"{NOTION_API}/pages",
        headers=_headers(token),
        json={
            "parent": {"database_id": database_id},
            "properties": {
                title_prop: {"title": [{"text": {"content": title}}]},
            },
        },
        timeout=15,
    )
    page_resp.raise_for_status()
    page_id = page_resp.json()["id"]
    page_url = page_resp.json().get("url", "")

    # Add prompt as a paragraph block
    requests.patch(
        f"{NOTION_API}/blocks/{page_id}/children",
        headers=_headers(token),
        json={
            "children": [
                {
                    "type": "callout",
                    "callout": {
                        "icon": {"type": "emoji", "emoji": "✦"},
                        "color": "purple_background",
                        "rich_text": [{"type": "text", "text": {"content": f"Prompt: {prompt}"}}],
                    },
                }
            ]
        },
        timeout=15,
    )

    # Try to upload the image
    image_uploaded = _upload_image_to_notion(token, page_id, image_bytes)

    return {
        "page_id": page_id,
        "page_url": page_url,
        "image_uploaded": image_uploaded,
    }
