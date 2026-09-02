import customtkinter as ctk
import logging
import logging.handlers
import sys
import os
from config import APP_NAME, LOG_PATH, APP_VERSION, ensure_app_folders
from database.db import init_db
from database.settings_repo import get_setting, set_setting
from ui.login import LoginFrame
from ui.shell import AppShell
from cloud.drive_sync import sync_pending_in_background

# Ensure folders exist before logging
ensure_app_folders()

# Rotating log file - 2 MB max, keep 3 backups
handler = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=2*1024*1024, backupCount=3, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
# Also add stream handler for console if dev
if not getattr(sys, "frozen", False):
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

logging.info("Starting %s version: %s", APP_NAME, APP_VERSION)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - v{APP_VERSION}")
        self.geometry("1280x760")
        self.minsize(1100, 650)

        try:
            init_db()
        except Exception as e:
            logging.exception("DB init failed: %s", e)
            # Show error dialog via tkinter if customtkinter not ready
            import tkinter.messagebox as mb
            mb.showerror("Database Error", f"Failed to initialize database:\n{e}\n\nCheck AppData folder permissions.")
            sys.exit(1)

        # Load saved theme
        theme = (get_setting("theme_mode", "light") or "light").lower()
        if theme not in ("light", "dark"):
            theme = "light"

        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self.show_login()

    def clear_screen(self):
        for widget in self.winfo_children():
            try:
                widget.destroy()
            except:
                pass

    def toggle_theme(self):
        current = (ctk.get_appearance_mode() or "Light").lower()
        new_theme = "dark" if current == "light" else "light"
        ctk.set_appearance_mode(new_theme)
        set_setting("theme_mode", new_theme)
        logging.info("Theme toggled to %s", new_theme)

    def show_login(self):
        self.clear_screen()
        frame = LoginFrame(self, on_success=self.show_app)
        frame.pack(expand=True, fill="both")

    def show_app(self):
        self.clear_screen()
        try:
            shell = AppShell(self, on_logout=self.show_login, on_toggle_theme=self.toggle_theme)
        except Exception as e:
            # Never leave the user with a blank window: report and return to login.
            logging.exception("AppShell failed to load: %s", e)
            import tkinter.messagebox as mb
            mb.showerror(
                "Startup Error",
                f"The main screen failed to load:\n{e}\n\nDetails were written to the log:\n{LOG_PATH}",
            )
            self.show_login()
            return
        # Start drive sync in background with error handling
        try:
            sync_pending_in_background()
        except Exception as e:
            logging.warning("Drive sync background start failed: %s", e)
        shell.pack(expand=True, fill="both")
        logging.info("AppShell loaded")


if __name__ == "__main__":
    try:
        app = App()
        # Set icon if exists
        try:
            import os
            from config import RESOURCE_DIR
            icon_path = os.path.join(RESOURCE_DIR, "assets", "app.ico")
            if os.path.exists(icon_path) and sys.platform == "win32":
                app.iconbitmap(icon_path)
        except Exception:
            pass
        app.mainloop()
    except KeyboardInterrupt:
        logging.info("App interrupted by user")
    except Exception as e:
        logging.exception("Unhandled exception: %s", e)
        try:
            import tkinter.messagebox as mb
            mb.showerror("Unexpected Error", f"An unexpected error occurred:\n{e}\n\nCheck logs at:\n{LOG_PATH}")
        except:
            pass
