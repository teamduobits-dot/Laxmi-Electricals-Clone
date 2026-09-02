import os
import customtkinter as ctk
from PIL import Image
from config import RESOURCE_DIR, APP_VERSION
from utils.auth import has_admin_password, set_admin_password, check_login
from ui.theme import APP_BG, SURFACE, BORDER, TEXT, TEXT_MUTED, PRIMARY, PRIMARY_HOV, FONT_FAMILY


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color=APP_BG)
        self.on_success = on_success
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.mode = "SETUP" if not has_admin_password() else "LOGIN"

        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=20, border_width=1, border_color=BORDER, width=400)
        card.grid(row=0, column=0, sticky="n", pady=70)
        card.grid_columnconfigure(0, weight=1)

        # Logo
        self.logo_img = None
        logo_path = os.path.join(RESOURCE_DIR, "assets", "logo_left.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
                ctk.CTkLabel(card, image=self.logo_img, text="").grid(row=0, column=0, pady=(28, 12))
            except:
                pass

        ctk.CTkLabel(card, text="Laxmi Electricals", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold")).grid(row=1, column=0, padx=40, pady=(0, 2))
        ctk.CTkLabel(card, text="Billing • Professional", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=12)).grid(row=2, column=0, padx=40, pady=(0, 18))

        # Mode badge
        badge_text = "🔒 First Time Setup • Create Admin Password" if self.mode == "SETUP" else "🔐 Secure Login"
        badge_fg = ("#DBEAFE", "#1E3A5F") if self.mode == "SETUP" else ("#DCFCE7", "#064E3B")
        badge_tx = ("#1E40AF", "#BFDBFE") if self.mode == "SETUP" else ("#166534", "#BBF7D0")
        ctk.CTkLabel(card, text=badge_text, fg_color=badge_fg, text_color=badge_tx, corner_radius=20, height=28, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")).grid(row=3, column=0, padx=40, pady=(0, 18), sticky="ew")

        # Form
        self.password_entry = ctk.CTkEntry(card, show="*", width=320, height=44, placeholder_text="Enter password", border_width=1, border_color=BORDER, corner_radius=10, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self.password_entry.grid(row=4, column=0, padx=40, pady=(0, 10))
        self.password_entry.focus_set()

        self.confirm_entry = None
        if self.mode == "SETUP":
            self.confirm_entry = ctk.CTkEntry(card, show="*", width=320, height=44, placeholder_text="Confirm password", border_width=1, border_color=BORDER, corner_radius=10, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
            self.confirm_entry.grid(row=5, column=0, padx=40, pady=(0, 10))
            tip = ctk.CTkLabel(card, text="💡 Password must be at least 4 characters. Keep it safe!", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=10), wraplength=300, justify="left")
            tip.grid(row=6, column=0, padx=40, pady=(0, 6), sticky="w")

        self.msg = ctk.CTkLabel(card, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=11), wraplength=300, justify="left", anchor="w")
        self.msg.grid(row=7, column=0, padx=40, pady=(6, 0), sticky="w")

        btn_text = "✓ Create & Continue" if self.mode == "SETUP" else "→ Login to Dashboard"
        self.button = ctk.CTkButton(card, text=btn_text, width=320, height=44, corner_radius=10, fg_color=PRIMARY, hover_color=PRIMARY_HOV, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.submit)
        self.button.grid(row=8, column=0, padx=40, pady=(16, 10))

        ctk.CTkLabel(card, text=f"© Laxmi Electricals • v{APP_VERSION} • Made in Pune", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=10)).grid(row=9, column=0, pady=(0, 24))

        self.password_entry.bind("<Return>", lambda e: self.submit())
        if self.confirm_entry:
            self.confirm_entry.bind("<Return>", lambda e: self.submit())

    def submit(self):
        pw = self.password_entry.get().strip()
        if len(pw) < 4:
            self.msg.configure(text="⚠ Password must be at least 4 characters.")
            return
        if self.mode == "SETUP":
            pw2 = self.confirm_entry.get().strip() if self.confirm_entry else ""
            if not pw2:
                self.msg.configure(text="Please confirm your password.")
                return
            if pw != pw2:
                self.msg.configure(text="⚠ Passwords do not match — please check.")
                return
            try:
                set_admin_password(pw)
            except Exception as e:
                self.msg.configure(text=str(e))
                return
            self.on_success()
            return
        if check_login(pw):
            self.on_success()
        else:
            self.msg.configure(text="❌ Invalid password — try again.")
