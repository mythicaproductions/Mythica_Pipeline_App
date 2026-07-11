"""Settings dialog — plain tkinter, works on Tk 8.5."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.credentials import save_credential, get_credential, OPENAI_KEY, NOTION_TOKEN

_BG    = "#1a1a2e"
_DEEP  = "#0d1220"
_TEXT  = "#dde0ff"
_MUTED = "#9090cc"
_LABEL = ("Helvetica Neue", 12)
_ENTRY = ("Helvetica Neue", 12)
_TITLE = ("Helvetica Neue", 17, "bold")
_BTN   = ("Helvetica Neue", 12, "bold")


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=_BG)
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()
        # Center on parent
        self.geometry("520x300")
        self._build_ui()
        self._load_saved()

    def _build_ui(self):
        pad = dict(padx=28, pady=10)

        tk.Label(self, text="API Credentials",
                 font=_TITLE, fg="#c8c0ff", bg=_BG,
                 ).pack(pady=(22, 10))

        sep = tk.Frame(self, bg="#2a2a4a", height=1)
        sep.pack(fill="x", padx=28, pady=(0, 12))

        # OpenAI key row
        row1 = tk.Frame(self, bg=_BG)
        row1.pack(fill="x", **pad)
        tk.Label(row1, text="OpenAI API Key", font=_LABEL,
                 fg=_MUTED, bg=_BG, width=16, anchor="e",
                 ).pack(side="left", padx=(0, 10))
        self._openai_var = tk.StringVar()
        self._openai_entry = tk.Entry(row1, textvariable=self._openai_var,
                                      show="•", font=_ENTRY,
                                      bg=_DEEP, fg=_TEXT, insertbackground=_TEXT,
                                      relief="flat", bd=4, width=30)
        self._openai_entry.pack(side="left", expand=True, fill="x")
        tk.Button(row1, text="Show", font=("Helvetica Neue", 10),
                  command=self._toggle_openai,
                  relief="flat", bd=0, bg="#252545", fg=_TEXT,
                  activebackground="#353565", activeforeground=_TEXT,
                  padx=8, pady=2,
                  ).pack(side="left", padx=(8, 0))

        # Notion token row
        row2 = tk.Frame(self, bg=_BG)
        row2.pack(fill="x", **pad)
        tk.Label(row2, text="Notion Token", font=_LABEL,
                 fg=_MUTED, bg=_BG, width=16, anchor="e",
                 ).pack(side="left", padx=(0, 10))
        self._notion_var = tk.StringVar()
        self._notion_entry = tk.Entry(row2, textvariable=self._notion_var,
                                      show="•", font=_ENTRY,
                                      bg=_DEEP, fg=_TEXT, insertbackground=_TEXT,
                                      relief="flat", bd=4, width=30)
        self._notion_entry.pack(side="left", expand=True, fill="x")
        tk.Button(row2, text="Show", font=("Helvetica Neue", 10),
                  command=self._toggle_notion,
                  relief="flat", bd=0, bg="#252545", fg=_TEXT,
                  activebackground="#353565", activeforeground=_TEXT,
                  padx=8, pady=2,
                  ).pack(side="left", padx=(8, 0))

        # Status
        self._status = tk.Label(self, text="", font=("Helvetica Neue", 11),
                                fg="#44cc88", bg=_BG)
        self._status.pack(pady=(4, 0))

        # Buttons
        btn_row = tk.Frame(self, bg=_BG)
        btn_row.pack(pady=18)
        tk.Button(btn_row, text="Cancel", font=_BTN,
                  bg="#3a3a3a", fg="white", activebackground="#555555",
                  relief="flat", bd=0, padx=20, pady=8,
                  command=self.destroy,
                  ).pack(side="left", padx=10)
        tk.Button(btn_row, text="Save", font=_BTN,
                  bg="#5a28b8", fg="white", activebackground="#7040d0",
                  relief="flat", bd=0, padx=20, pady=8,
                  command=self._save,
                  ).pack(side="left", padx=10)

    def _load_saved(self):
        for key, entry in ((OPENAI_KEY, self._openai_entry), (NOTION_TOKEN, self._notion_entry)):
            val = get_credential(key)
            if val:
                entry.insert(0, val)

    def _toggle_openai(self):
        self._openai_entry.configure(
            show="" if self._openai_entry.cget("show") == "•" else "•")

    def _toggle_notion(self):
        self._notion_entry.configure(
            show="" if self._notion_entry.cget("show") == "•" else "•")

    def _save(self):
        key = self._openai_var.get().strip()
        tok = self._notion_var.get().strip()
        if key:
            save_credential(OPENAI_KEY, key)
        if tok:
            save_credential(NOTION_TOKEN, tok)
        self._status.configure(text="Saved to macOS Keychain ✓")
        self.after(1200, self.destroy)
