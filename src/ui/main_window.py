"""Main application window — plain tkinter, works on Tk 8.5 (macOS system Python)."""

from __future__ import annotations

import io
import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.openai_service import generate_image, edit_image
from utils.credentials import get_credential, OPENAI_KEY, NOTION_TOKEN

# DnD — graceful fallback if native lib is incompatible
_HAS_DND = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD as _TkDnD
    _HAS_DND = True
except Exception:
    pass

_OUTPUT_DIR = Path.home() / "Documents" / "Mythica Pipeline"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Palette
_BG      = "#12121e"
_PANEL   = "#1a1a2e"
_DEEP    = "#0d1220"
_DROP_BG = "#0f1e3a"
_DROP_BD = "#2a3a6a"
_ACCENT  = "#5a28b8"
_ACCENT2 = "#6a38c8"
_NOTION  = "#1a4a3a"
_NOTION2 = "#2a6a5a"
_TEXT    = "#dde0ff"
_MUTED   = "#7788cc"
_DIM     = "#445577"
_HDR     = "#0e0e1c"

_FONT_TITLE  = ("Helvetica Neue", 19, "bold")
_FONT_LABEL  = ("Helvetica Neue", 12, "bold")
_FONT_BODY   = ("Helvetica Neue", 13)
_FONT_BTN_LG = ("Helvetica Neue", 14, "bold")
_FONT_BTN_SM = ("Helvetica Neue", 11)
_FONT_STATUS = ("Helvetica Neue", 11)


# ── Reusable canvas-backed button ─────────────────────────────────────────────
# tk.Button on macOS Aqua ignores `bg`; tk.Label + binding gives full control.

class _FlatBtn:
    """Label-backed button: respects bg/fg on all macOS Tk versions."""

    def __init__(self, parent, text, bg, fg="#ffffff",
                 font=_FONT_BTN_LG, command=None, height=42, padx=0):
        self._bg = bg
        self._bg_hover = _lighten(bg, 28)
        self._fg = fg
        self._text = text
        self._font = font
        self._command = command
        self._enabled = True

        self._frame = tk.Frame(parent, bg=bg, height=height, cursor="hand2")
        self._label = tk.Label(
            self._frame, text=text, bg=bg, fg=fg,
            font=font, cursor="hand2", padx=padx or 16,
        )
        self._label.pack(expand=True, fill="both")

        for w in (self._frame, self._label):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>",    self._enter)
            w.bind("<Leave>",    self._leave)

    def _click(self, _e=None):
        if self._enabled and self._command:
            self._command()

    def _enter(self, _e=None):
        if self._enabled:
            self._frame.configure(bg=self._bg_hover)
            self._label.configure(bg=self._bg_hover)

    def _leave(self, _e=None):
        col = self._bg if self._enabled else _darken(self._bg, 40)
        self._frame.configure(bg=col)
        self._label.configure(bg=col)

    def configure(self, text=None, state=None, command=None):
        if text is not None:
            self._text = text
            self._label.configure(text=text)
        if state is not None:
            self._enabled = (state == "normal")
            col = self._bg if self._enabled else _darken(self._bg, 40)
            fg  = self._fg if self._enabled else _darken(self._fg, 60)
            self._frame.configure(bg=col)
            self._label.configure(bg=col, fg=fg)
        if command is not None:
            self._command = command

    def grid(self, **kw):        self._frame.grid(**kw)
    def grid_forget(self):       self._frame.grid_forget()
    def pack(self, **kw):        self._frame.pack(**kw)
    def pack_forget(self):       self._frame.pack_forget()


def _lighten(hex_c: str, amt: int = 20) -> str:
    r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
    return f"#{min(255,r+amt):02x}{min(255,g+amt):02x}{min(255,b+amt):02x}"

def _darken(hex_c: str, amt: int = 20) -> str:
    r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
    return f"#{max(0,r-amt):02x}{max(0,g-amt):02x}{max(0,b-amt):02x}"


# ── Main application ───────────────────────────────────────────────────────────

class MythicaApp:
    def __init__(self):
        if _HAS_DND:
            try:
                self.root = _TkDnD.Tk()
                self._dnd_active = True
            except Exception:
                self.root = tk.Tk()
                self._dnd_active = False
        else:
            self.root = tk.Tk()
            self._dnd_active = False

        self.root.title("Mythica Pipeline")
        self.root.geometry("1060x700")
        self.root.minsize(840, 560)
        self.root.configure(bg=_BG)

        self.reference_path: str | None = None
        self.generated_bytes: bytes | None = None
        self._last_prompt = ""
        self._ref_photo = None   # keep ImageTk ref alive
        self._gen_photo = None

        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_body()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=_HDR, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="Mythica Pipeline",
                 font=_FONT_TITLE, fg="#c8c0ff", bg=_HDR,
                 ).pack(side="left", padx=22)

        _FlatBtn(hdr, "⚙  Settings", "#252545", font=_FONT_BTN_SM,
                 command=self._open_settings, height=34,
                 ).pack(side="right", padx=18, pady=10)

    def _build_body(self):
        body = tk.Frame(self.root, bg=_BG)
        body.pack(fill="both", expand=True, padx=18, pady=14)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=_PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))

        right = tk.Frame(body, bg=_PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))

        self._build_left(left)
        self._build_right(right)

    # ── Left panel ────────────────────────────────────────────────────────────

    def _build_left(self, parent):
        parent.grid_rowconfigure(0, weight=3)   # drop zone
        parent.grid_rowconfigure(1, weight=0)   # clear btn
        parent.grid_rowconfigure(2, weight=0)   # "Prompt" label
        parent.grid_rowconfigure(3, weight=2)   # prompt textbox
        parent.grid_rowconfigure(4, weight=0)   # size selector
        parent.grid_rowconfigure(5, weight=0)   # generate btn
        parent.grid_columnconfigure(0, weight=1)

        # Drop zone
        self._drop_zone = tk.Frame(
            parent, bg=_DROP_BG,
            highlightbackground="#5566cc", highlightthickness=2,
        )
        self._drop_zone.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 6))
        self._drop_zone.grid_rowconfigure(0, weight=1)
        self._drop_zone.grid_columnconfigure(0, weight=1)

        self._drop_label = tk.Label(
            self._drop_zone,
            text="Drop Reference Photo Here\n\nor click here to browse files\n(optional — leave empty to generate from prompt)",
            font=_FONT_BODY, fg="#c0ccff", bg=_DROP_BG,
            justify="center", cursor="hand2",
        )
        self._drop_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self._drop_img_lbl = tk.Label(self._drop_zone, bg=_DROP_BG, cursor="hand2")

        for w in (self._drop_zone, self._drop_label):
            w.bind("<Button-1>", self._browse_file)

        if self._dnd_active:
            for w in (self._drop_zone, self._drop_label):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_dnd_drop)

        # Clear btn (hidden until a reference is loaded)
        self._clear_btn = _FlatBtn(
            parent, "✕  Clear Reference Photo",
            "#3a0010", font=_FONT_BTN_SM, height=28, command=self._clear_reference,
        )

        # Prompt label
        tk.Label(parent, text="Prompt", font=_FONT_LABEL,
                 fg="#9090cc", bg=_PANEL,
                 ).grid(row=2, column=0, sticky="w", padx=20, pady=(8, 2))

        # Prompt textbox
        txt_frame = tk.Frame(parent, bg=_PANEL)
        txt_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 8))
        txt_frame.grid_rowconfigure(0, weight=1)
        txt_frame.grid_columnconfigure(0, weight=1)

        self._prompt = tk.Text(
            txt_frame, wrap="word",
            bg=_DEEP, fg=_DIM, insertbackground=_TEXT,
            font=_FONT_BODY, relief="flat", bd=4,
            padx=8, pady=8,
        )
        self._prompt.grid(row=0, column=0, sticky="nsew")
        sb = tk.Scrollbar(txt_frame, command=self._prompt.yview,
                          bg=_PANEL, troughcolor=_DEEP, bd=0)
        sb.grid(row=0, column=1, sticky="ns")
        self._prompt.configure(yscrollcommand=sb.set)

        self._PLACEHOLDER = "Describe what you want to create…"
        self._prompt.insert("1.0", self._PLACEHOLDER)
        self._prompt.bind("<FocusIn>",  self._prompt_focus_in)
        self._prompt.bind("<FocusOut>", self._prompt_focus_out)

        # Size selector
        size_row = tk.Frame(parent, bg=_PANEL)
        size_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 6))
        tk.Label(size_row, text="Size:", font=_FONT_LABEL,
                 fg="#9090cc", bg=_PANEL).pack(side="left", padx=(0, 8))

        self._SIZE_MAP = {
            "Square 1:1  (1024×1024)":      "1024x1024",
            "Landscape 3:2  (1536×1024)":   "1536x1024",
            "Portrait 2:3  (1024×1536)":    "1024x1536",
            "Landscape 16:9  (1792×1024)":  "1792x1024",
            "Portrait 9:16  (1024×1792)":   "1024x1792",
        }
        self._size_var = tk.StringVar(value="Square 1:1  (1024×1024)")
        size_menu = tk.OptionMenu(size_row, self._size_var, *self._SIZE_MAP.keys())
        size_menu.configure(
            bg=_DEEP, fg="#c0ccff", activebackground="#252545",
            activeforeground="#c0ccff", font=_FONT_BODY,
            relief="flat", bd=0, highlightthickness=0, direction="above",
        )
        size_menu["menu"].configure(bg=_DEEP, fg="#c0ccff", font=_FONT_BODY,
                                    activebackground="#252545", activeforeground="#c0ccff")
        size_menu.pack(side="left", fill="x", expand=True)

        # Generate button
        self._gen_btn = _FlatBtn(
            parent, "✦  Generate Image", _ACCENT,
            font=_FONT_BTN_LG, command=self._generate, height=48,
        )
        self._gen_btn.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 16))

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=0)
        parent.grid_rowconfigure(2, weight=0)
        parent.grid_columnconfigure(0, weight=1)

        self._result_frame = tk.Frame(parent, bg=_DEEP)
        self._result_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 6))
        self._result_frame.grid_rowconfigure(0, weight=1)
        self._result_frame.grid_columnconfigure(0, weight=1)

        self._result_label = tk.Label(
            self._result_frame,
            text="Generated image\nwill appear here",
            font=_FONT_BODY, fg="#c0ccff", bg=_DEEP,
            justify="center",
        )
        self._result_label.grid(row=0, column=0, sticky="nsew")

        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            parent, textvariable=self._status_var,
            font=_FONT_STATUS, fg=_MUTED, bg=_PANEL,
        )
        self._status_lbl.grid(row=1, column=0, pady=(0, 4))

        # Two-button row: Save locally  |  Save to Notion
        btn_row = tk.Frame(parent, bg=_PANEL)
        btn_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self._save_btn = _FlatBtn(
            btn_row, "💾  Save Image", "#2a3a6a",
            font=_FONT_BTN_LG, command=self._save_locally, height=44,
        )
        self._save_btn.configure(state="disabled")
        self._save_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self._notion_btn = _FlatBtn(
            btn_row, "📄  Save to Notion", _NOTION,
            font=_FONT_BTN_LG, command=self._save_to_notion, height=44,
        )
        self._notion_btn.configure(state="disabled")
        self._notion_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    # ── Drop zone ─────────────────────────────────────────────────────────────

    def _on_dnd_drop(self, event):
        raw = event.data.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        self._load_reference(raw.split("} {")[0].strip("{} "))

    def _browse_file(self, _e=None):
        path = filedialog.askopenfilename(
            title="Select Reference Photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tiff"),
                       ("All Files", "*.*")],
        )
        if path:
            self._load_reference(path)

    def _load_reference(self, path: str):
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((320, 260), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._ref_photo = photo  # prevent GC

            self._drop_label.grid_forget()
            self._drop_img_lbl.configure(image=photo)
            self._drop_img_lbl.grid(row=0, column=0, padx=8, pady=8)
            self._drop_img_lbl.bind("<Button-1>", self._browse_file)
            if self._dnd_active:
                self._drop_img_lbl.drop_target_register(DND_FILES)
                self._drop_img_lbl.dnd_bind("<<Drop>>", self._on_dnd_drop)

            self.reference_path = path
            self._clear_btn.grid(row=1, column=0, padx=70, pady=(0, 6), sticky="ew")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open image:\n{exc}", parent=self.root)

    def _clear_reference(self):
        self.reference_path = None
        self._ref_photo = None
        self._drop_img_lbl.grid_forget()
        self._drop_img_lbl.configure(image="")
        self._drop_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self._clear_btn.grid_forget()

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _prompt_focus_in(self, _e=None):
        if self._prompt.get("1.0", "end").strip() == self._PLACEHOLDER:
            self._prompt.delete("1.0", "end")
            self._prompt.configure(fg=_TEXT)

    def _prompt_focus_out(self, _e=None):
        if not self._prompt.get("1.0", "end").strip():
            self._prompt.insert("1.0", self._PLACEHOLDER)
            self._prompt.configure(fg=_DIM)

    def _get_prompt(self) -> str:
        t = self._prompt.get("1.0", "end").strip()
        return "" if t == self._PLACEHOLDER else t

    # ── Generation ────────────────────────────────────────────────────────────

    def _generate(self):
        prompt = self._get_prompt()
        if not prompt:
            messagebox.showwarning("Prompt required", "Please type a prompt first.", parent=self.root)
            return
        api_key = get_credential(OPENAI_KEY)
        if not api_key:
            messagebox.showwarning("No API key",
                "Open Settings (⚙ top right) and add your OpenAI API key.",
                parent=self.root)
            return

        self._last_prompt = prompt
        self._gen_btn.configure(text="Generating…", state="disabled")
        self._save_btn.configure(state="disabled")
        self._notion_btn.configure(state="disabled")
        self._set_status("Calling OpenAI…", "#9999ff")

        size = self._SIZE_MAP[self._size_var.get()]

        def _run():
            try:
                data = (edit_image(api_key, self.reference_path, prompt, size)
                        if self.reference_path
                        else generate_image(api_key, prompt, size))
                self.root.after(0, lambda: self._on_generated(data))
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda: self._on_gen_error(err))

        threading.Thread(target=_run, daemon=True).start()

    def _on_generated(self, image_bytes: bytes):
        self.generated_bytes = image_bytes

        fname = f"mythica_{int(time.time())}.png"
        (_OUTPUT_DIR / fname).write_bytes(image_bytes)

        img = Image.open(io.BytesIO(image_bytes))
        fw = max(self._result_frame.winfo_width()  - 32, 460)
        fh = max(self._result_frame.winfo_height() - 32, 460)
        img.thumbnail((fw, fh), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._gen_photo = photo  # prevent GC

        self._result_label.configure(image=photo, text="", bg=_DEEP)
        self._result_label.image = photo

        self._set_status(f"Auto-saved to ~/Documents/Mythica Pipeline/{fname}", "#44cc88")
        self._gen_btn.configure(text="✦  Generate Image", state="normal")
        self._save_btn.configure(state="normal")
        self._notion_btn.configure(state="normal")

    def _on_gen_error(self, error: str):
        self._set_status("Generation failed.", "#cc4444")
        self._gen_btn.configure(text="✦  Generate Image", state="normal")
        messagebox.showerror("Generation failed", error, parent=self.root)

    # ── Save locally ──────────────────────────────────────────────────────────

    def _save_locally(self):
        if not self.generated_bytes:
            return
        from tkinter import filedialog
        dest = filedialog.asksaveasfilename(
            title="Save Image",
            initialdir=Path.home() / "Desktop",
            initialfile=f"mythica_{int(time.time())}.png",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All Files", "*.*")],
        )
        if dest:
            Path(dest).write_bytes(self.generated_bytes)
            self._set_status(f"Saved to {dest}", "#44cc88")

    # ── Notion ────────────────────────────────────────────────────────────────

    def _save_to_notion(self):
        token = get_credential(NOTION_TOKEN)
        if not token:
            messagebox.showwarning("No Notion token",
                "Open Settings (⚙ top right) and add your Notion Integration Token.",
                parent=self.root)
            return
        from ui.notion_dialog import NotionSaveDialog
        NotionSaveDialog(self.root, token, self.generated_bytes, self._last_prompt)

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self.root)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, msg: str, color: str = _MUTED):
        self._status_var.set(msg)
        self._status_lbl.configure(fg=color)
        self.root.update_idletasks()

    def run(self):
        self.root.mainloop()
