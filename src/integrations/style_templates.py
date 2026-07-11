"""Style templates — selectable named styles (replaces a single baked-in style).

For the skeleton these live in code. TODO: move to a Notion database so they can
be edited without redeploying the server (see CLAUDE.md §3.2). The `pnw_forest`
entry is the style from the original spec, now just one option among many.
"""
from __future__ import annotations

_TEMPLATES: dict[str, str] = {
    "pnw_forest": (
        "Photographic realism, Pacific Northwest forest environment, dappled "
        "natural light filtering through canopy, earth tones and deep greens, "
        "subtle golden light from sunlight not artificial glow, no fantasy "
        "illustration style, no stock photo energy"
    ),
}


def get_template(name: str) -> str:
    if name not in _TEMPLATES:
        raise ValueError(
            f"Unknown style template '{name}'. Available: {sorted(_TEMPLATES)}"
        )
    return _TEMPLATES[name]


def list_templates() -> list[dict]:
    return [{"name": k, "prefix": v} for k, v in _TEMPLATES.items()]
