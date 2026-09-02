import customtkinter as ctk
from datetime import datetime
import os
from PIL import Image

from ui.theme import (
    APP_BG, SURFACE, BORDER, TEXT, TEXT_MUTED,
    SIDEBAR_BG, SIDEBAR_HOVER, SIDEBAR_TEXT,
    PRIMARY, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV,
    FONT_FAMILY
)
from config import RESOURCE_DIR

from ui.dashboard import DashboardPage
from ui.customers import CustomersPage
from ui.services import ServicesPage
from ui.billing import BillingPage
from ui.bills import BillsPage
from ui.dues import DuesPage
from ui.reports import ReportsPage
from ui.settings import SettingsPage


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_nav, on_logout):
        super().__init__(master, width=250, corner_radius=0, fg_color=SIDEBAR_BG)
        self.on_nav = on_nav
        self.on_logout = on_logout
        self.buttons = {}

        # Logo + brand
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(20, 10))

        logo_path = os.path.join(RESOURCE_DIR, "assets", "logo_left.png")
        self.logo_img = None
        if os.path.exists(logo_path):
            try:
                pil = Image.open(logo_path)
                self.logo_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(38, 38))
                ctk.CTkLabel(header, image=self.logo_img, text="").pack(side="left", padx=(0,10))
            except:
                pass

        brand_box = ctk.CTkFrame(header, fg_color="transparent")
        brand_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(brand_box, text="Laxmi", text_color="white",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=19, weight="bold"), anchor="w").pack(anchor="w")
        ctk.CTkLabel(brand_box, text="Electricals", text_color="#96A4C8",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12), anchor="w").pack(anchor="w")

        ctk.CTkFrame(self, height=1, fg_color="#1A2642").pack(fill="x", padx=18, pady=(14, 16))

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="both", expand=True, padx=12, pady=10)

        # Icons using unicode
        self._add_nav_button(nav, "◧  Dashboard", "dashboard")
        self._add_nav_button(nav, "👥  Customers", "customers")
        self._add_nav_button(nav, "🛠  Services", "services")
        self._add_nav_button(nav, "＋  Create Bill", "billing")
        self._add_nav_button(nav, "≡  Bills History", "bills")
        self._add_nav_button(nav, "◷  Pending Dues", "dues")
        self._add_nav_button(nav, "▭  Reports", "reports")
        self._add_nav_button(nav, "⚙  Settings", "settings")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=16)

        ctk.CTkFrame(footer, height=1, fg_color="#1A2642").pack(fill="x", pady=(0,12))

        logout_btn = ctk.CTkButton(
            footer, text="⎋  Logout", height=42,
            fg_color="transparent", hover_color=SIDEBAR_HOVER,
            text_color=SIDEBAR_TEXT, anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            command=self.on_logout
        )
        logout_btn.pack(fill="x")

        # Footer version
        ctk.CTkLabel(footer, text="v1.1 • Professional", text_color="#556888",
                     font=ctk.CTkFont(size=10), anchor="w").pack(fill="x", pady=(8,0), padx=6)

        self.set_active("dashboard")

    def _add_nav_button(self, parent, text, key):
        btn = ctk.CTkButton(
            parent,
            text=text,
            height=44,
            corner_radius=10,
            fg_color="transparent",
            hover_color=SIDEBAR_HOVER,
            text_color=SIDEBAR_TEXT,
            anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            command=lambda: self.on_nav(key)
        )
        btn.pack(fill="x", pady=3, padx=2)
        self.buttons[key] = btn

    def set_active(self, key):
        for k, b in self.buttons.items():
            if k == key:
                b.configure(fg_color=PRIMARY, text_color="white")
            else:
                b.configure(fg_color="transparent", text_color=SIDEBAR_TEXT)


class Topbar(ctk.CTkFrame):
    def __init__(self, master, on_toggle_theme):
        super().__init__(master, corner_radius=14, fg_color=SURFACE, border_width=1, border_color=BORDER)
        self.on_toggle_theme = on_toggle_theme

        self.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=18, pady=14)

        self.title_label = ctk.CTkLabel(left, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"), text_color=TEXT, anchor="w")
        self.title_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(left, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_MUTED, anchor="w")
        self.subtitle_label.pack(anchor="w", pady=(2,0))

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=12)

        date_str = datetime.now().strftime("%a, %d %b %Y")
        self.date_label = ctk.CTkLabel(right, text=date_str, text_color=TEXT_MUTED,
                                       font=ctk.CTkFont(family=FONT_FAMILY, size=12))
        self.date_label.pack(side="left", padx=(0, 14))

        self.theme_btn = ctk.CTkButton(
            right, text="◐ Theme", width=88, height=32,
            corner_radius=20,
            fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX,
            hover_color=BTN_SOFT_HV,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self.on_toggle_theme
        )
        self.theme_btn.pack(side="left", padx=(0, 10))

        chip = ctk.CTkFrame(right, fg_color=("#EEF2FF", "#1E293B"), corner_radius=20)
        chip.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(chip, text="●", text_color=("#16A34A","#22C55E"), font=ctk.CTkFont(size=10)).pack(side="left", padx=(10,2), pady=6)
        self.user_label = ctk.CTkLabel(chip, text="Owner", text_color=TEXT,
                                       font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"))
        self.user_label.pack(side="left", padx=(0,10), pady=6)

    def set_title(self, text: str):
        titles = {
            "Dashboard": "Welcome back 👋",
            "Customers": "Manage your customer database",
            "Services": "Service catalog & pricing",
            "Create Bill": "Generate a new professional invoice",
            "Bills History": "All invoices & transactions",
            "Pending Dues": "Track & collect payments",
            "Reports": "Business insights & exports",
            "Settings": "App configuration & backup"
        }
        self.title_label.configure(text=text)
        self.subtitle_label.configure(text=titles.get(text, ""))


class AppShell(ctk.CTkFrame):
    def __init__(self, master, on_logout, on_toggle_theme):
        super().__init__(master, fg_color=APP_BG)
        self.on_logout = on_logout
        self.on_toggle_theme = on_toggle_theme

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = Sidebar(self, on_nav=self.show_page, on_logout=self.on_logout)
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.topbar = Topbar(right, on_toggle_theme=self.on_toggle_theme)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))

        self.content = ctk.CTkFrame(right, corner_radius=18, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.pages_config = {
            "dashboard": (DashboardPage, "Dashboard"),
            "customers": (CustomersPage, "Customers"),
            "services": (ServicesPage, "Services"),
            "billing": (BillingPage, "Create Bill"),
            "bills": (BillsPage, "Bills History"),
            "dues": (DuesPage, "Pending Dues"),
            "reports": (ReportsPage, "Reports"),
            "settings": (SettingsPage, "Settings"),
        }

        self.page_instances = {}
        self.current_page = None
        self.show_page("dashboard")

    def show_page(self, key: str):
        if key not in self.pages_config:
            return

        if self.current_page:
            self.current_page.grid_forget()

        PageClass, title = self.pages_config[key]
        self.topbar.set_title(title)
        self.sidebar.set_active(key)

        if key not in self.page_instances:
            try:
                try:
                    page = PageClass(self.content, navigate=self.show_page)
                except TypeError:
                    page = PageClass(self.content)
            except Exception as e:
                # A broken page must never take down the whole shell.
                import logging
                logging.exception("Failed to build page '%s': %s", key, e)
                page = self._build_error_page(key, e)
                page.grid(row=0, column=0, sticky="nsew")
                self.current_page = page
                return
            self.page_instances[key] = page
            page.grid(row=0, column=0, sticky="nsew")
        else:
            page = self.page_instances[key]
            page.grid(row=0, column=0, sticky="nsew")
            if hasattr(page, "load_lookups"):
                try:
                    page.load_lookups()
                except:
                    pass
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except:
                    pass

        self.current_page = page

    def _build_error_page(self, key: str, error: Exception):
        frame = ctk.CTkFrame(self.content, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        ctk.CTkLabel(
            frame, text="⚠ This page failed to load",
            text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")
        ).pack(pady=(48, 8))
        ctk.CTkLabel(
            frame,
            text=f"Page: {key}\nError: {error}\n\nDetails were saved to the app log.\nRe-open this page from the sidebar to retry.",
            text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=12), justify="center"
        ).pack(padx=30)
        return frame
