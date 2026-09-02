import tkinter as tk
from tkinter import font as tkfont

class SuggestionPopup:
    """
    Modern bigger suggestion dropdown for Entry/CTkEntry with keyboard nav.
    """
    def __init__(self, entry, on_select):
        self.entry = entry
        self.on_select = on_select
        self.top = None
        self.listbox = None
        self.values = []
        self.max_height_px = 300
        self.row_height_px = 32
        self.min_width_px = 420
        self.font_size = 11
        self.entry.bind("<Down>", self._focus_listbox)
        self.entry.bind("<Escape>", lambda e: self.hide())
        self.entry.bind("<FocusOut>", lambda e: self.entry.after(200, self._hide_if_focus_lost))

    def show(self, values):
        self.values = list(values or [])
        if not self.values:
            self.hide()
            return
        if self.top is None or not self.top.winfo_exists():
            self.top = tk.Toplevel(self.entry.winfo_toplevel())
            self.top.overrideredirect(True)
            self.top.attributes("-topmost", True)
            # Border frame
            outer = tk.Frame(self.top, bg="#E5E7EB", bd=1)
            outer.pack(fill="both", expand=True)
            inner = tk.Frame(outer, bg="white")
            inner.pack(fill="both", expand=True, padx=1, pady=1)

            lb_font = tkfont.Font(family="Segoe UI", size=self.font_size)
            self.listbox = tk.Listbox(
                inner,
                activestyle="none",
                font=lb_font,
                bg="white",
                fg="#0F172A",
                selectbackground="#DBEAFE",
                selectforeground="#1E40AF",
                relief="flat",
                bd=0,
                highlightthickness=0
            )
            self.listbox.pack(fill="both", expand=True, padx=4, pady=4)

            self.listbox.bind("<Double-Button-1>", lambda e: self._pick())
            self.listbox.bind("<Return>", lambda e: self._pick())
            self.listbox.bind("<Escape>", lambda e: self.hide())
            self.listbox.bind("<FocusOut>", lambda e: self.top.after(200, self._hide_if_focus_lost))

            # Scrollbar styling
            try:
                sb = tk.Scrollbar(inner, orient="vertical", command=self.listbox.yview)
                self.listbox.configure(yscrollcommand=sb.set)
                sb.pack(side="right", fill="y")
            except:
                pass

        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 4
        entry_w = self.entry.winfo_width()
        w = max(entry_w, self.min_width_px)
        # Adjust for screen edge
        screen_w = self.entry.winfo_toplevel().winfo_screenwidth()
        if x + w > screen_w - 20:
            x = max(10, screen_w - w - 20)

        desired_h = self.row_height_px * len(self.values) + 16
        h = min(self.max_height_px, max(60, desired_h))
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        self.listbox.delete(0, "end")
        for v in self.values:
            self.listbox.insert("end", f"  {v}")

        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(0)
        self.listbox.activate(0)
        self.top.deiconify()
        self.top.lift()

    def hide(self):
        if self.top and self.top.winfo_exists():
            self.top.withdraw()

    def _hide_if_focus_lost(self):
        try:
            # If toplevel not focused, hide
            entry_focus = self.entry.winfo_toplevel().focus_get()
            # Keep visible if focus is entry or listbox or popup
            if entry_focus in (self.entry, self.listbox):
                return
            # If entry still has text and popup visible, don't hide immediately if mouse over?
            self.hide()
        except:
            try:
                self.hide()
            except:
                pass

    def _focus_listbox(self, _e=None):
        if self.top and self.top.winfo_exists() and str(self.top.state()) != "withdrawn":
            self.listbox.focus_set()
            return "break"

    def _pick(self):
        if not self.listbox:
            return
        sel = self.listbox.curselection()
        if not sel:
            return
        value = self.listbox.get(sel[0]).strip()
        self.hide()
        self.entry.focus_set()
        self.on_select(value)
