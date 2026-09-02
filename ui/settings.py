import os
import platform
import subprocess
import customtkinter as ctk
from tkinter import messagebox, filedialog

from config import BUSINESS_NAME, BUSINESS_PHONE, BUSINESS_ADDRESS, BILLS_DIR, BACKUP_DIR, DB_PATH, APP_VERSION
from database.settings_repo import get_business_profile, save_business_profile, get_setting, set_setting
from utils.auth import change_admin_password
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, PRIMARY, PRIMARY_HOV, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, SUCCESS, SUCCESS_HOV, FONT_FAMILY
from utils.backup import create_local_backup, list_backups, cleanup_old_backups


def open_folder(path):
    if not path or not os.path.exists(path):
        messagebox.showinfo("Open Folder", "Folder does not exist yet.")
        return
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Open Folder", str(e))


class ChangePasswordForm(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Change Password")
        self.geometry("500x380")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        box.pack(expand=True, fill="both", padx=16, pady=16)
        box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(box, text="🔒 Change Password", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18,14))
        ctk.CTkLabel(box, text="Current Password", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=1, column=0, sticky="w", padx=18, pady=10)
        self.current = ctk.CTkEntry(box, show="*", height=36, border_width=1, border_color=BORDER, placeholder_text="Enter current password")
        self.current.grid(row=1, column=1, sticky="ew", padx=18, pady=10)
        ctk.CTkLabel(box, text="New Password", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=2, column=0, sticky="w", padx=18, pady=10)
        self.new = ctk.CTkEntry(box, show="*", height=36, border_width=1, border_color=BORDER, placeholder_text="Min 4 characters")
        self.new.grid(row=2, column=1, sticky="ew", padx=18, pady=10)
        ctk.CTkLabel(box, text="Confirm New", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=3, column=0, sticky="w", padx=18, pady=10)
        self.confirm = ctk.CTkEntry(box, show="*", height=36, border_width=1, border_color=BORDER, placeholder_text="Repeat new password")
        self.confirm.grid(row=3, column=1, sticky="ew", padx=18, pady=10)
        self.msg = ctk.CTkLabel(box, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.msg.grid(row=4, column=0, columnspan=2, sticky="w", padx=18, pady=(0,8))
        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.grid(row=5, column=0, columnspan=2, sticky="e", padx=18, pady=(12,18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, command=self.destroy).pack(side="right", padx=(10,0))
        ctk.CTkButton(btns, text="✓ Update Password", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.save).pack(side="right")
        self.current.focus_set()
        self.confirm.bind("<Return>", lambda e: self.save())

    def save(self):
        cur = self.current.get().strip()
        new = self.new.get().strip()
        conf = self.confirm.get().strip()
        if not cur:
            self.msg.configure(text="Current password required.")
            return
        if len(new)<4:
            self.msg.configure(text="New password must be at least 4 characters.")
            return
        if new != conf:
            self.msg.configure(text="New password and confirm do not match.")
            return
        if cur == new:
            self.msg.configure(text="New password must be different from current.")
            return
        try:
            change_admin_password(cur, new)
            messagebox.showinfo("Password", "✓ Password updated successfully! Use new password next login.")
            self.destroy()
        except Exception as e:
            self.msg.configure(text=str(e))


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0,14))
        ctk.CTkLabel(header, text="Settings", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text=f"v{APP_VERSION} • Professional Edition", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(12,0))
        ctk.CTkButton(header, text="📂 Open Data Folder", width=140, height=32, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=11), command=lambda: open_folder(os.path.dirname(DB_PATH))).pack(side="right")

        self._business_card()
        self._appearance_card()
        self._storage_card()
        self._backup_card()
        self._security_card()
        self._about_card()

    def _section_card(self, icon, title, subtitle):
        card = ctk.CTkFrame(self.scroll, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0,14))
        card.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16,8))
        ctk.CTkLabel(head, text=f"{icon}  {title}", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text=subtitle, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(10,0))
        return card

    def _business_card(self):
        card = self._section_card("🏢", "Business Profile", "Shown on every invoice — editable")
        card.grid_columnconfigure(1, weight=1)
        profile = get_business_profile(BUSINESS_NAME, BUSINESS_PHONE, BUSINESS_ADDRESS)
        ctk.CTkLabel(card, text="Business Name *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=1, column=0, sticky="w", padx=18, pady=10)
        self.name_entry = ctk.CTkEntry(card, height=36, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=12))
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=18, pady=10)
        self.name_entry.insert(0, profile["name"])

        ctk.CTkLabel(card, text="Phone", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=2, column=0, sticky="w", padx=18, pady=10)
        self.phone_entry = ctk.CTkEntry(card, height=36, border_width=1, border_color=BORDER)
        self.phone_entry.grid(row=2, column=1, sticky="ew", padx=18, pady=10)
        self.phone_entry.insert(0, profile["phone"])

        ctk.CTkLabel(card, text="Address", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=3, column=0, sticky="nw", padx=18, pady=10)
        self.address_box = ctk.CTkTextbox(card, height=90, border_width=1, border_color=BORDER, corner_radius=10)
        self.address_box.grid(row=3, column=1, sticky="ew", padx=18, pady=10)
        self.address_box.insert("1.0", profile["address"])

        ctk.CTkButton(card, text="✓ Save Business Details", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.save_business).grid(row=4, column=0, columnspan=2, sticky="e", padx=18, pady=(6,18))

    def _appearance_card(self):
        card = self._section_card("🎨", "Appearance", "Light / Dark theme")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Theme Mode", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=1, column=0, sticky="w", padx=18, pady=12)
        saved_theme = (get_setting("theme_mode","light") or "light").lower()
        if saved_theme not in ("light","dark"):
            saved_theme="light"
        self.theme_var = ctk.StringVar(value=saved_theme)
        self.theme_menu = ctk.CTkOptionMenu(card, values=["light","dark"], variable=self.theme_var, width=120, height=32, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.theme_menu.grid(row=1, column=1, sticky="w", padx=18, pady=12)
        ctk.CTkButton(card, text="Apply Theme", width=120, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, command=self.apply_theme).grid(row=1, column=2, sticky="e", padx=18, pady=12)

    def _storage_card(self):
        card = self._section_card("💾", "Bills Storage", "Choose where PDFs are saved — optionally inside Google Drive Desktop folder")
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Tip: Select a folder inside Google Drive 'My Drive' to auto-sync invoices to cloud.", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11), wraplength=600, justify="left").grid(row=1, column=0, columnspan=3, sticky="w", padx=18, pady=(0,12))
        ctk.CTkLabel(card, text="Bills Folder Path", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).grid(row=2, column=0, sticky="w", padx=18, pady=10)
        saved = (get_setting("bills_base_dir","") or "").strip()
        if not saved:
            saved = BILLS_DIR
        self.bills_dir_entry = ctk.CTkEntry(card, height=36, border_width=1, border_color=BORDER)
        self.bills_dir_entry.grid(row=2, column=1, sticky="ew", padx=18, pady=10)
        self.bills_dir_entry.insert(0, saved)
        ctk.CTkButton(card, text="Browse...", width=90, height=32, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, command=self.browse_bills_dir).grid(row=2, column=2, sticky="e", padx=18, pady=10)
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=3, sticky="e", padx=18, pady=(6,18))
        ctk.CTkButton(btns, text="💾 Save Folder", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.save_bills_dir).pack(side="left", padx=(0,10))
        ctk.CTkButton(btns, text="📂 Open Folder", fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, command=self.open_bills_folder).pack(side="left")

    def _backup_card(self):
        card = self._section_card("🛡", "Data Backup & Safety", "Protect your database with local backups")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Regular backups prevent data loss. Recommended: backup weekly and before major updates.", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11), wraplength=600, justify="left").grid(row=1, column=0, sticky="w", padx=18, pady=(0,10))
        self.last_backup_lbl = ctk.CTkLabel(card, text="Last Backup: —", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.last_backup_lbl.grid(row=2, column=0, sticky="w", padx=18, pady=6)
        backups = list_backups()
        if backups:
            last = os.path.basename(backups[0])
            import time
            mtime = time.strftime("%d-%m-%Y %H:%M", time.localtime(os.path.getmtime(backups[0])))
            self.last_backup_lbl.configure(text=f"Last Backup: {last} ({mtime}) • {len(backups)} backups saved")

        # Stats
        stat_frame = ctk.CTkFrame(card, fg_color="#F8FAFC", corner_radius=10)
        stat_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=8)
        try:
            db_size = os.path.getsize(DB_PATH) / (1024*1024)
            ctk.CTkLabel(stat_frame, text=f"DB Size: {db_size:.2f} MB", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=14, pady=10)
            ctk.CTkLabel(stat_frame, text=f"Backups: {len(backups)}", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=14, pady=10)
        except:
            pass

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="e", padx=18, pady=(6,18))
        ctk.CTkButton(btns, text="🛡 Create Backup Now", fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.run_backup).pack(side="left", padx=(0,10))
        ctk.CTkButton(btns, text="📂 Open Backups Folder", fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, command=self.open_backups_folder).pack(side="left")

    def _security_card(self):
        card = self._section_card("🔒", "Security", "Password & access control")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Your app is protected by a local admin password. Change it regularly and keep it safe.", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11), wraplength=600, justify="left").grid(row=1, column=0, sticky="w", padx=18, pady=(0,12))
        ctk.CTkButton(card, text="🔑 Change Login Password", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, command=lambda: ChangePasswordForm(self)).grid(row=2, column=0, sticky="e", padx=18, pady=(0,18))

    def _about_card(self):
        card = self._section_card("ℹ", "About", f"Laxmi Electricals Billing Professional v{APP_VERSION}")
        card.grid_columnconfigure(0, weight=1)
        info = f"Built with Python + CustomTkinter + SQLite • ReportLab PDF\nBusiness: {BUSINESS_NAME}\nSupport: Team DuoBits"
        ctk.CTkLabel(card, text=info, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11), justify="left").grid(row=1, column=0, sticky="w", padx=18, pady=(0,18))

    # Actions
    def run_backup(self):
        try:
            path = create_local_backup()
            cleanup_old_backups(20)
            backups = list_backups()
            if backups:
                import time
                last = os.path.basename(backups[0])
                mtime = time.strftime("%d-%m-%Y %H:%M", time.localtime(os.path.getmtime(backups[0])))
                self.last_backup_lbl.configure(text=f"Last Backup: {last} ({mtime}) • {len(backups)} backups saved")
            messagebox.showinfo("Backup", f"✓ Database backup created successfully!\n\nSaved to:\n{path}\n\nTip: Copy this file to Google Drive or pen drive for extra safety.")
        except Exception as e:
            messagebox.showerror("Backup Failed", str(e))

    def open_backups_folder(self):
        open_folder(BACKUP_DIR)

    def browse_bills_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.bills_dir_entry.delete(0,"end")
            self.bills_dir_entry.insert(0, folder)

    def save_bills_dir(self):
        folder = self.bills_dir_entry.get().strip()
        if not folder:
            messagebox.showerror("Bills Folder", "Please select a folder.")
            return
        try:
            os.makedirs(folder, exist_ok=True)
            test_file = os.path.join(folder, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            messagebox.showerror("Bills Folder", f"Cannot use this folder:\n{e}")
            return
        set_setting("bills_base_dir", folder)
        messagebox.showinfo("Bills Folder", f"✓ Saved!\n\nNew invoices will be saved in:\n{folder}\n\nExisting PDFs stay in old location.")

    def open_bills_folder(self):
        folder = self.bills_dir_entry.get().strip()
        open_folder(folder)

    def save_business(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        address = self.address_box.get("1.0","end").strip()
        if not name or len(name)<2:
            messagebox.showerror("Business", "Business name must be at least 2 characters.")
            return
        if len(address)<5:
            messagebox.showwarning("Business", "Address seems too short — please add full address for invoice.")
            return
        save_business_profile(name, phone, address)
        messagebox.showinfo("Saved", "✓ Business details saved!\n\nNew invoices will use these details immediately.\nExisting PDFs unchanged unless regenerated.")

    def apply_theme(self):
        mode = (self.theme_var.get() or "light").lower()
        if mode not in ("light","dark"):
            mode="light"
        ctk.set_appearance_mode(mode)
        set_setting("theme_mode", mode)
        messagebox.showinfo("Theme", f"✓ Theme changed to {mode.capitalize()}!\nRestart app for full effect on some elements.")
