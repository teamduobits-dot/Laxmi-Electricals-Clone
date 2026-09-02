import os
import socket
import platform
import subprocess
import threading
import customtkinter as ctk
from tkinter import messagebox

from database.dashboard_repo import get_dashboard_stats, get_recent_bills
from utils.storage import best_pdf_path_for_bill_number, get_pdf_path
from utils.date_utils import fmt_date
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, CARD_BG, ROW_BG, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, PRIMARY, PRIMARY_HOV, FONT_FAMILY


def money(v) -> str:
    try:
        return f"₹{float(v):,.2f}"
    except:
        return "₹0.00"

def is_online() -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=0.8)
        return True
    except:
        return False

def open_pdf_file(bill_no: str):
    p = best_pdf_path_for_bill_number(bill_no) or get_pdf_path(bill_no)
    if not os.path.exists(p):
        messagebox.showerror("PDF", f"PDF not found:\n{p}")
        return
    try:
        if platform.system() == "Windows":
            os.startfile(p)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception as e:
        messagebox.showerror("Open PDF", str(e))


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, navigate=None):
        super().__init__(master, fg_color="transparent")
        self.navigate = navigate

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        # Header row
        top = ctk.CTkFrame(self.scroll, fg_color="transparent")
        top.pack(fill="x", pady=(0, 16))

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Business Overview", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text="Track your daily performance and pending actions", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=12)).pack(anchor="w", pady=(2,0))

        right = ctk.CTkFrame(top, fg_color="transparent")
        right.pack(side="right")

        # Online badge starts neutral; the network probe runs off the UI thread
        self.online_badge = ctk.CTkLabel(
            right, text="○ Checking…",
            fg_color=("#F1F5F9", "#1E293B"), text_color=TEXT_MUTED,
            corner_radius=20, width=88, height=28, anchor="center",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        )
        self.online_badge.pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            right, text="+  New Bill", height=36, width=120,
            corner_radius=10,
            fg_color=PRIMARY, hover_color=PRIMARY_HOV,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=lambda: self.navigate("billing") if self.navigate else None
        ).pack(side="left")

        # Stats cards - 4 in row with icons
        stats_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 16))
        for i in range(4):
            stats_row.grid_columnconfigure(i, weight=1, uniform="stats")

        self.card_today = self._stat_card(stats_row, "Today's Collection", "₹0", "💰", ("#DBEAFE","#1E3A5F"))
        self.card_month = self._stat_card(stats_row, "Monthly Revenue", "₹0", "📈", ("#DCFCE7","#064E3B"))
        self.card_pending = self._stat_card(stats_row, "Pending Amount", "₹0", "⏳", ("#FFEDD5","#7C2D12"))
        self.card_active = self._stat_card(stats_row, "Active Customers", "0", "👥", ("#F3E8FF","#581C87"))

        self.card_today.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.card_month.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.card_pending.grid(row=0, column=2, sticky="ew", padx=(0, 10))
        self.card_active.grid(row=0, column=3, sticky="ew")

        # Mid row: Quick Actions + Alerts
        mid = ctk.CTkFrame(self.scroll, fg_color="transparent")
        mid.pack(fill="x", pady=(0, 16))
        mid.grid_columnconfigure(0, weight=2)
        mid.grid_columnconfigure(1, weight=1)

        # Quick Actions
        qa = ctk.CTkFrame(mid, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        qa.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        qa.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(qa, text="Quick Actions", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 10))

        grid = ctk.CTkFrame(qa, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        for i in range(4):
            grid.grid_columnconfigure(i, weight=1, uniform="qa")

        self._qa_btn(grid, "Create Bill", "＋", lambda: self.navigate("billing")).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._qa_btn(grid, "Collect Payment", "₹", lambda: self.navigate("dues")).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self._qa_btn(grid, "Add Customer", "👤", lambda: self.navigate("customers")).grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self._qa_btn(grid, "Update Rates", "🛠", lambda: self.navigate("services")).grid(row=0, column=3, sticky="ew")

        # Alerts
        self.alerts = ctk.CTkFrame(mid, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        self.alerts.grid(row=0, column=1, sticky="nsew")
        self.alerts.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.alerts, text="⚠ Alerts", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(16,8))
        
        self.alert_box = ctk.CTkFrame(self.alerts, fg_color=("#FFF7ED","#431407"), corner_radius=12, border_width=1, border_color=("#FDBA74","#7C2D12"))
        self.alert_box.grid(row=1, column=0, sticky="ew", padx=16, pady=(0,16))
        self.alert_box.grid_columnconfigure(0, weight=1)
        
        self.alert_label = ctk.CTkLabel(self.alert_box, text="", text_color=TEXT, justify="left", font=ctk.CTkFont(family=FONT_FAMILY, size=12))
        self.alert_label.grid(row=0, column=0, sticky="w", padx=14, pady=12)

        ctk.CTkButton(
            self.alert_box, text="View Dues →", width=100, height=30,
            fg_color=("#F97316","#EA580C"), hover_color=("#EA580C","#C2410C"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=lambda: self.navigate("dues") if self.navigate else None
        ).grid(row=0, column=1, sticky="e", padx=12, pady=12)

        # Recent Bills
        self._recent_bills_section()
        self.refresh()

        # Probe connectivity off the UI thread so the page never blocks on the network
        threading.Thread(target=self._probe_online, daemon=True, name="DashboardOnline").start()

    def _probe_online(self):
        online = is_online()
        try:
            self.after(0, lambda: self._apply_online_badge(online))
        except Exception:
            pass  # widget already destroyed

    def _apply_online_badge(self, online: bool):
        try:
            if not self.online_badge.winfo_exists():
                return
            badge_text = "● Online" if online else "○ Offline"
            badge_fg = ("#DCFCE7", "#064E3B") if online else ("#FEE2E2", "#7F1D1D")
            badge_tx = ("#166534", "#A7F3D0") if online else ("#991B1B", "#FCA5A5")
            self.online_badge.configure(text=badge_text, fg_color=badge_fg, text_color=badge_tx)
        except Exception:
            pass

    def _stat_card(self, parent, title, value, icon, color_pair):
        f = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        f.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14,0))
        ctk.CTkLabel(top, text=icon, fg_color=color_pair, width=34, height=34, corner_radius=10, text_color=TEXT).pack(side="left")
        ctk.CTkLabel(top, text=title, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(10,0))
        v = ctk.CTkLabel(f, text=value, text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"), anchor="w")
        v.pack(anchor="w", padx=16, pady=(10, 16))
        f.value_label = v
        return f

    def _qa_btn(self, parent, text, icon, cmd):
        btn = ctk.CTkButton(
            parent, text=f"{icon}\n{text}", height=70,
            fg_color=CARD_BG, text_color=TEXT,
            border_width=1, border_color=BORDER,
            hover_color=("#F8FAFC","#1E293B"),
            corner_radius=12,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=lambda: cmd() if cmd else None
        )
        return btn

    def _recent_bills_section(self):
        box = ctk.CTkFrame(self.scroll, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        box.pack(fill="both", expand=True)
        box.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(box, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        ctk.CTkLabel(head, text="Recent Bills", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(head, text="View All →", width=90, height=28, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                      command=lambda: self.navigate("bills") if self.navigate else None).pack(side="right")

        self.rows = ctk.CTkScrollableFrame(box, fg_color="transparent")
        self.rows.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))

    def refresh(self):
        s = get_dashboard_stats()
        self.card_today.value_label.configure(text=money(s["today_earnings"]))
        self.card_month.value_label.configure(text=money(s["month_earnings"]))
        self.card_pending.value_label.configure(text=money(s["pending_dues"]))
        self.card_active.value_label.configure(text=str(s["active_customers"]))

        if s['pending_count'] > 0:
            self.alert_label.configure(text=f"{s['pending_count']} pending bills\nDue: {money(s['pending_dues'])} needs attention")
            self.alerts.configure(fg_color=SURFACE)
        else:
            self.alert_label.configure(text="All clear! No pending dues 🎉")
        
        for w in self.rows.winfo_children():
            w.destroy()

        bills = get_recent_bills(10)
        if not bills:
            ctk.CTkLabel(self.rows, text="No bills yet. Create your first bill to see it here.", text_color=TEXT_MUTED,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=12)).pack(pady=24)
            return

        # Header row for recent
        hdr = ctk.CTkFrame(self.rows, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(0,6))
        for txt, w in [("Bill No",110), ("Date",100), ("Customer",1), ("Amount",120), ("",90)]:
            if w==1:
                hdr.grid_columnconfigure(2, weight=1)
            ctk.CTkLabel(hdr, text=txt, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=0, column=["Bill No","Date","Customer","Amount",""].index(txt), sticky="w" if txt!="Amount" else "e", padx=6)

        for b in bills:
            rf = ctk.CTkFrame(self.rows, fg_color=ROW_BG, corner_radius=12)
            rf.pack(fill="x", padx=6, pady=4)
            inner = ctk.CTkFrame(rf, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=10)
            inner.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(inner, text=b["bill_number"], text_color=TEXT, width=110, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(inner, text=fmt_date(b.get("created_at")), text_color=TEXT_MUTED, width=100, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(inner, text=b.get("customer_name",""), text_color=TEXT, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=12)).grid(row=0, column=2, sticky="ew", padx=(6, 6))
            ctk.CTkLabel(inner, text=money(b.get("total_amount",0)), text_color=TEXT, width=120, anchor="e", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")).grid(row=0, column=3, sticky="e")

            ctk.CTkButton(
                inner, text="Open", width=76, height=26,
                fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX,
                hover_color=BTN_SOFT_HV,
                corner_radius=8,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                command=lambda bn=b["bill_number"]: open_pdf_file(bn)
            ).grid(row=0, column=4, sticky="e", padx=(10, 0))
