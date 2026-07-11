"""Notion save dialog — plain tkinter, works on Tk 8.5."""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.notion_service import list_databases, get_database_title, create_page_with_image

_BG    = "#1a1a2e"
_DEEP  = "#0d1220"
_TEXT  = "#dde0ff"
_MUTED = "#9090cc"
_LABEL = ("Helvetica Neue", 12)
_ENTRY = ("Helvetica Neue", 12)
_TITLE = ("Helvetica Neue", 16, "bold")
_BTN   = ("Helvetica Neue", 12, "bold")


class NotionSaveDialog(tk.Toplevel):
    def __init__(self, parent, token: str, image_bytes: bytes, prompt: str):
        super().__init__(parent)
        self.title("Save to Notion")
        self.configure(bg=_BG)
        self.geometry("480x310")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.token = token
        self.image_bytes = image_bytes
        self.prompt = prompt
        self.databases = []

        self._build_ui()
        self._load_databases()

    def _build_ui(self):
        tk.Label(self, text="Save to Notion",
                 font=_TITLE, fg="#c8c0ff", bg=_BG,
                 ).pack(pady=(20, 8))

        sep = tk.Frame(self, bg="#2a2a4a", height=1)
        sep.pack(fill="x", padx=28, pady=(0, 14))

        pad = dict(padx=28, pady=8)

        # Database picker
        row1 = tk.Frame(self, bg=_BG)
        row1.pack(fill="x", **pad)
        tk.Label(row1, text="Database:", font=_LABEL,
                 fg=_MUTED, bg=_BG, width=12, anchor="e",
                 ).pack(side="left", padx=(0, 10))
        self._db_var = tk.StringVar(value="Loading databases…")
        self._db_menu = tk.OptionMenu(row1, self._db_var, "Loading databases…")
        self._db_menu.configure(
            bg=_DEEP, fg=_TEXT, activebackground="#252545",
            activeforeground=_TEXT, font=_LABEL,
            relief="flat", bd=0, highlightthickness=0,
        )
        self._db_menu["menu"].configure(bg=_DEEP, fg=_TEXT, font=_LABEL)
        self._db_menu.pack(side="left", fill="x", expand=True)

        # Page title
        row2 = tk.Frame(self, bg=_BG)
        row2.pack(fill="x", **pad)
        tk.Label(row2, text="Page title:", font=_LABEL,
                 fg=_MUTED, bg=_BG, width=12, anchor="e",
                 ).pack(side="left", padx=(0, 10))
        self._title_var = tk.StringVar(value="Mythica Generated Image")
        tk.Entry(row2, textvariable=self._title_var,
                 font=_ENTRY, bg=_DEEP, fg=_TEXT,
                 insertbackground=_TEXT, relief="flat", bd=4,
                 ).pack(side="left", fill="x", expand=True)

        # Status
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(self, textvariable=self._status_var,
                                    font=("Helvetica Neue", 11),
                                    fg=_MUTED, bg=_BG)
        self._status_lbl.pack(pady=(4, 0))

        # Buttons
        btn_row = tk.Frame(self, bg=_BG)
        btn_row.pack(pady=18)
        tk.Button(btn_row, text="Cancel", font=_BTN,
                  bg="#3a3a3a", fg="white", activebackground="#555555",
                  relief="flat", bd=0, padx=20, pady=8,
                  command=self.destroy,
                  ).pack(side="left", padx=10)
        self._save_btn = tk.Button(btn_row, text="Save to Notion", font=_BTN,
                                   bg="#1a4a3a", fg="white", activebackground="#2a6a5a",
                                   relief="flat", bd=0, padx=20, pady=8,
                                   command=self._do_save)
        self._save_btn.pack(side="left", padx=10)

    def _set_status(self, msg: str, color: str = _MUTED):
        self._status_var.set(msg)
        self._status_lbl.configure(fg=color)

    def _load_databases(self):
        def run():
            try:
                dbs = list_databases(self.token)
                self.databases = dbs
                names = [get_database_title(db) for db in dbs] or \
                        ["No databases found — check token permissions"]
                self.after(0, lambda: self._populate_menu(names))
            except Exception as exc:
                err = str(exc)
                self.after(0, lambda: self._set_status(f"Error: {err}", "#cc4444"))
        threading.Thread(target=run, daemon=True).start()

    def _populate_menu(self, names: list):
        menu = self._db_menu["menu"]
        menu.delete(0, "end")
        for name in names:
            menu.add_command(label=name,
                             command=lambda n=name: self._db_var.set(n))
        self._db_var.set(names[0])

    def _get_selected_db_id(self) -> str | None:
        selected = self._db_var.get()
        for db in self.databases:
            if get_database_title(db) == selected:
                return db["id"]
        return None

    def _do_save(self):
        db_id = self._get_selected_db_id()
        if not db_id:
            self._set_status("Please select a valid database.", "#cc8800")
            return
        title = self._title_var.get().strip() or "Mythica Generated Image"

        self._save_btn.configure(state="disabled", text="Saving…")
        self._set_status("Uploading to Notion…", "#aaaaff")

        def run():
            try:
                result = create_page_with_image(
                    self.token, db_id, title, self.prompt, self.image_bytes)
                self.after(0, lambda: self._on_saved(result))
            except Exception as exc:
                err = str(exc)
                self.after(0, lambda: self._on_error(err))
        threading.Thread(target=run, daemon=True).start()

    def _on_saved(self, result: dict):
        msg = ("Page created with image ✓" if result["image_uploaded"]
               else "Page created — image attachment requires Notion file-upload access ✓")
        self._set_status(msg, "#44cc88")
        self._save_btn.configure(text="Saved ✓")
        self.after(2000, self.destroy)

    def _on_error(self, error: str):
        self._set_status(f"Error: {error}", "#cc4444")
        self._save_btn.configure(state="normal", text="Save to Notion")
