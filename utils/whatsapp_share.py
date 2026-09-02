import os
import platform
import subprocess
import urllib.parse
import logging

def normalize_phone_for_whatsapp(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 10:
        return "91" + digits
    if len(digits) == 11 and digits.startswith("0"):
        return "91" + digits[1:]
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    return digits

def open_whatsapp_chat(phone: str, message: str):
    ph = normalize_phone_for_whatsapp(phone)
    if not ph or len(ph) < 10:
        raise ValueError("Customer phone number is missing/invalid (need 10 digits).")

    text = urllib.parse.quote(message or "")
    url = f"https://wa.me/{ph}?text={text}"

    try:
        system = platform.system()
        if system == "Windows":
            # Use os.startfile if url?
            subprocess.Popen(f'start "" "{url}"', shell=True)
        elif system == "Darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        logging.info(f"Opened WhatsApp chat for {ph}")
    except Exception as e:
        logging.error(f"Failed to open WhatsApp: {e}")
        raise ValueError(f"Could not open WhatsApp browser:\n{e}")

def reveal_file_in_explorer(file_path: str):
    if not file_path:
        return
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        logging.warning(f"File to reveal does not exist: {file_path}")
        return
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(f'explorer /select,"{file_path}"')
        elif system == "Darwin":
            subprocess.Popen(["open", "-R", file_path])
        else:
            # Linux: open containing folder
            subprocess.Popen(["xdg-open", os.path.dirname(file_path)])
        logging.info(f"Revealed file in explorer: {file_path}")
    except Exception as e:
        logging.warning(f"Failed to reveal file {file_path}: {e}")

def get_whatsapp_preview_url(phone: str, message: str) -> str:
    """Return URL without opening - for debugging"""
    ph = normalize_phone_for_whatsapp(phone)
    text = urllib.parse.quote(message or "")
    return f"https://wa.me/{ph}?text={text}"
