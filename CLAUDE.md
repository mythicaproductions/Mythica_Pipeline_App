# Mythica Pipeline — Architecture

> **Status:** This document is the agreed **architecture plan**. The desktop app
> described in "Existing app" is built and working today. The **MCP server layer**
> is planned and not yet built. Sections marked _(planned)_ describe target design,
> not current code.

---

## 1. What this project is

Two independent ways to drive the same image-generation engine:

1. **Desktop app** _(exists today)_ — a Tkinter GUI on the user's Mac. Upload
   reference images, generate via OpenAI, view results locally.
2. **Remote MCP server** _(planned)_ — an always-on cloud service that exposes the
   same generation capability as callable tools, so it can be driven from
   **ClickUp Brain** (and Claude Desktop) over the internet.

The desktop app is **not** being rebuilt or refactored. The MCP server is a second
"doorway" onto the shared engine. The GUI code (`src/ui/`) is out of scope.

### Why a custom server instead of ClickUp Brain's native image generation

ClickUp Brain can generate images natively, but it bills ClickUp credits and is
costly at volume. Routing through our own server lets us use the OpenAI API
(pay-per-image, cheaper at scale), apply reusable **style templates**, log every
generation to a **Notion library**, and **swap in other image generators** over
time. None of that is possible with Brain's built-in generator.

---

## 2. The round trip

```
  User types in ClickUp Brain:
  "generate a forest scene, style=pnw_forest, 1024x1024"
            │
            ▼
  ┌────────────────────┐
  │   ClickUp Brain    │  calls the registered MCP tool
  └────────────────────┘
            │  prompt + style template + size + provider
            ▼
  ┌──────────────────────────────────────┐
  │   MCP SERVER (cloud: Railway/Fly)     │  the switchboard
  │   1. auth check (API key)             │
  │   2. look up style template (Notion)  │
  │   3. route to provider adapter        │──► OpenAI / others
  │   4. get raw image bytes              │
  │   5. store image → get public URL     │──► Notion library
  │   6. log metadata (prompt/style/date) │──► Notion DB
  └──────────────────────────────────────┘
            │  image URL + metadata
            ▼
  ┌────────────────────┐
  │   ClickUp Brain    │  shows the image/link back in chat
  └────────────────────┘
            │
            ▼
  User grabs it in-field; optionally attaches to a task
```

**Key fact:** OpenAI returns raw image *bytes*, not a web link. To make an image
visible in ClickUp, the server must **store it somewhere public first** (step 5)
and return that link. This is the single most important reason storage exists in
this design.

---

## 3. Core components

### 3.1 Provider adapters (extensible generators)

One tool interface, swappable engines behind it. Each generator is a small,
self-contained adapter.

- **OpenAI adapter** — reuses the existing `src/services/openai_service.py`
  (`generate_image`, `edit_image`). This is the first and default provider.
- **Future adapters** — e.g. Stability, Flux/Replicate. Adding one = writing one
  new adapter file; the tool interface and everything else stays unchanged.

The MCP tool takes a `provider` argument that routes to the right adapter.

### 3.2 Style templates (selectable, not baked-in)

The original spec hardcoded a single Pacific-Northwest-forest style. That is
**replaced** by named, selectable templates.

- A template = a name + a descriptive text prefix prepended to the user's prompt.
- Templates are stored in **Notion** so they can be edited without redeploying.
- The tool takes a `style` argument naming which template to apply.

> The desktop app derives style from *uploaded reference images*. The ClickUp flow
> is text-driven, so text templates are the natural fit. Reference-image style in
> the cloud flow is handled via "reference-from-storage" (§3.4).

### 3.3 Storage & delivery

Designed specifically to avoid ClickUp task bloat.

| Layer | Role |
|-------|------|
| **Image host** | Where the image gets a publicly reachable URL. **Fast path (current): the MCP server hosts it itself** at `/images/<id>.png` (in-memory, ephemeral) — no separate bucket needed. **Future: R2/S3** for durable storage. Notion-hosted URLs are not reliably reachable by ClickUp, so they are not used as the host. |
| **ClickUp Brain chat** | **Delivery.** The image URL is returned into the chat; user views/downloads in-field. Inline display is the goal (see §9). |
| **Notion DB** | **Metadata library + data-back.** Every generation logged: prompt, style, provider, bucket URL, timestamp. Searchable archive — but Notion does **not** host the image itself. |
| **ClickUp task** | **Optional, manual only.** A separate action attaches an image to a task when the user chooses. Never auto-created. |

### 3.4 Reference-from-storage

For image-to-image ("use this image to inform the next one"):

- **Desktop app** already handles local references (and Eagle) — unchanged; use at
  the desk.
- **Cloud/ClickUp flow** — point the tool at a **stored image URL** (from the
  Notion library) as the reference. Same capability, sourced from the cloud.

---

## 4. Tools exposed by the MCP server _(planned)_

1. **`generate_image`** — `prompt`, `style` (template name), `size`, `provider`.
   Generates, stores, logs, returns the image URL + metadata.
2. **`list_style_templates`** — returns available style templates (read from
   Notion). _Replaces_ the original `generate_image_with_defaults` single-style
   tool.
3. **`list_recent_generations`** — returns the last N generations (URLs + metadata)
   from this session.

_(A manual `attach_to_task` tool may be added for the optional task-attachment
step in §3.3.)_

---

## 5. Cross-cutting concerns

### Auth
- **Server access:** API-key auth so only authorized clients (ClickUp, Claude
  Desktop) can call the tools.
- **Provider/service secrets:** OpenAI key, Notion token, ClickUp token.

### Secrets: keychain vs environment
The desktop app stores the OpenAI key in the **macOS keychain**
(`src/utils/credentials.py`). A cloud server has no keychain — the MCP server reads
all secrets from **environment variables** set on the host. The key therefore lives
in two places (Mac keychain for the GUI; host env vars for the server).

### Transport
**Streamable HTTP** (not stdio), so the server can be deployed remotely and reached
by ClickUp Brain.

### Library
`fastmcp`.

---

## 6. Deployment _(planned)_

- Target: **Railway or Fly.io** (Dockerfile-based).
- Artifacts to add: `Dockerfile` (and/or `Procfile`), updated `requirements.txt`
  with `fastmcp` + provider/integration deps.
- Secrets configured as host environment variables (see §5).

---

## 7. File structure

```
Mythica_Pipeline_App/
├── CLAUDE.md                     # this document
├── requirements.txt              # UPDATE: add fastmcp + new deps        (planned)
├── Dockerfile / Procfile         # NEW: deployment                       (planned)
├── src/
│   ├── main.py                   # desktop entry point — UNCHANGED
│   ├── mcp_server.py             # NEW: MCP server entry point           (planned)
│   ├── providers/                # NEW: generator adapters               (planned)
│   │   └── openai_adapter.py     #   wraps existing openai_service
│   ├── integrations/             # NEW: Notion + ClickUp helpers         (planned)
│   ├── services/
│   │   ├── openai_service.py     # EXISTING — reused, not duplicated
│   │   └── notion_service.py     # existing
│   ├── ui/                       # OUT OF SCOPE — do not modify
│   └── utils/
│       └── credentials.py        # existing (keychain, desktop only)
```

---

## 8. Explicitly out of scope

- **The GUI (`src/ui/`) is not modified.** The desktop app stays fully functional.
- No refactor of `openai_service.py` — it is reused as-is (via an adapter).

---

## 9. Decisions & remaining unknowns

**Decided:**
1. **Inline image is the goal.** We want the image visible in the Brain chat, not
   just a link. Approach: return the public bucket URL (and, if needed, MCP image
   content) and confirm inline rendering empirically once the server is live.
2. **Image host = public bucket (R2/S3), not Notion.** Notion-hosted URLs are not
   reliably reachable by ClickUp, so images are uploaded to a bucket for a permanent
   public URL. Notion holds metadata only.
3. **`list_recent_generations` stays simple for now** — in-memory, per-process. Get
   the app going first; revisit durability (read from Notion log) later.

**Still to nail down (during build):**
- Whether Brain renders a custom tool's image **inline** vs. as a link — test live.
- Exact bucket choice + credentials (Cloudflare R2 vs S3) — needed to implement
  `BucketStorage` in `src/integrations/storage.py`.

---

## 10. Skeleton status (built so far)

Scaffolded and compiling; **not yet runnable end-to-end** (needs `pip install
fastmcp` + `OPENAI_API_KEY`, and a real bucket for ClickUp-reachable URLs):

- `src/mcp_server.py` — FastMCP server, Streamable HTTP, API-key middleware, 3 tools
- `src/providers/` — `base.py`, `openai_provider.py` (reuses `openai_service`), registry
- `src/integrations/` — `style_templates.py` (in-code for now), `storage.py`
  (`datauri` dev backend + `BucketStorage` TODO)
- `Dockerfile`, `Procfile`, `.dockerignore`, `requirements-server.txt`, updated
  `requirements.txt`

**Not started:** bucket upload, Notion logging + template source, ClickUp task
attachment, live inline-render test.
```
