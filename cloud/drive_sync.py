import os
import threading
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from database.sync_repo import enqueue_upload, get_pending_uploads, mark_synced, mark_failed
from database.settings_repo import get_setting, set_setting

SCOPES = ["https://www.googleapis.com/auth/drive"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "cloud", "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "cloud", "token.json")

ROOT_FOLDER_NAME = "Laxmi_Electricals_Bills"

_sync_lock = threading.Lock()
_sync_running = False

def is_configured() -> bool:
    return os.path.exists(CREDENTIALS_PATH)

def get_drive_service():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"Missing credentials: {CREDENTIALS_PATH} - place your Google OAuth credentials.json here.")

    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            logging.warning(f"Failed to load token.json: {e}, will re-auth")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logging.info("Refreshed Google Drive token")
            except Exception as e:
                logging.warning(f"Token refresh failed: {e}, starting new flow")
                creds = None
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")
            logging.info("New Google Drive auth completed")

        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)

def _find_folder(service, name: str, parent_id: str | None):
    # Escape single quotes in name for query
    safe_name = name.replace("'", "\\'")
    if parent_id:
        q = f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{parent_id}' in parents"
    else:
        q = f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    try:
        res = service.files().list(q=q, fields="files(id, name)", pageSize=10).execute()
        files = res.get("files", [])
        return files[0]["id"] if files else None
    except HttpError as e:
        logging.warning(f"Find folder failed for {name}: {e}")
        return None

def _create_folder(service, name: str, parent_id: str | None):
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    try:
        folder = service.files().create(body=meta, fields="id").execute()
        logging.info(f"Created Drive folder {name} -> {folder['id']}")
        return folder["id"]
    except HttpError as e:
        logging.error(f"Create folder failed {name}: {e}")
        raise

def _validate_folder_id(service, folder_id: str) -> bool:
    """Check if cached folder ID still exists"""
    if not folder_id:
        return False
    try:
        service.files().get(fileId=folder_id, fields="id").execute()
        return True
    except:
        return False

def get_or_create_root_folder(service):
    cached = (get_setting("drive_root_folder_id", "") or "").strip()
    if cached and _validate_folder_id(service, cached):
        return cached
    elif cached:
        logging.warning(f"Cached root folder ID {cached} invalid, will recreate")
        set_setting("drive_root_folder_id", "")

    fid = _find_folder(service, ROOT_FOLDER_NAME, parent_id=None)
    if not fid:
        fid = _create_folder(service, ROOT_FOLDER_NAME, parent_id=None)
    set_setting("drive_root_folder_id", fid)
    return fid

def get_or_create_year_folder(service, root_id: str, year: str):
    key = f"drive_year_folder_id_{year}"
    cached = (get_setting(key, "") or "").strip()
    if cached and _validate_folder_id(service, cached):
        return cached
    elif cached:
        logging.warning(f"Cached year folder {year} ID {cached} invalid")
        set_setting(key, "")

    fid = _find_folder(service, year, parent_id=root_id)
    if not fid:
        fid = _create_folder(service, year, parent_id=root_id)
    set_setting(key, fid)
    return fid

def upload_pdf(service, folder_id: str, file_path: str, file_name: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    safe_fn = file_name.replace("'", "\\'")
    q = f"name='{safe_fn}' and trashed=false and '{folder_id}' in parents"
    try:
        res = service.files().list(q=q, fields="files(id,name,parents)", pageSize=5).execute()
        files = res.get("files", [])
    except HttpError as e:
        logging.warning(f"List files failed: {e}")
        files = []

    media = MediaFileUpload(file_path, mimetype="application/pdf", resumable=True)
    try:
        if files:
            file_id = files[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
            logging.info(f"Updated Drive file {file_name} in folder {folder_id}")
        else:
            meta = {"name": file_name, "parents": [folder_id]}
            service.files().create(body=meta, media_body=media).execute()
            logging.info(f"Uploaded Drive file {file_name} to folder {folder_id}")
    except HttpError as e:
        logging.error(f"Upload failed for {file_name}: {e}")
        raise

def try_upload_or_queue(bill_id: int, bill_number: str, pdf_path: str) -> str:
    if not is_configured():
        return "Drive not configured (skipped). Add credentials.json to enable auto backup."

    try:
        service = get_drive_service()
        year = str(bill_number).split("-")[0] if "-" in str(bill_number) else "Unknown"
        root_id = get_or_create_root_folder(service)
        year_id = get_or_create_year_folder(service, root_id, year)
        upload_pdf(service, year_id, pdf_path, f"{bill_number}.pdf")
        return "✓ Uploaded to Google Drive."
    except FileNotFoundError as e:
        logging.warning(f"Drive upload file not found: {e}")
        return f"File not found: {e}"
    except Exception as e:
        logging.warning(f"Drive upload failed, queuing: {e}")
        try:
            enqueue_upload(bill_id, pdf_path)
        except Exception as qe:
            logging.error(f"Failed to enqueue: {qe}")
        return "⟳ Queued for Drive sync (offline / will retry)."

def sync_pending_uploads(max_items: int = 30) -> dict:
    if not is_configured():
        return {"ok": False, "message": "Drive not configured."}

    try:
        service = get_drive_service()
        root_id = get_or_create_root_folder(service)
    except Exception as e:
        logging.error(f"Drive service init failed in sync: {e}")
        return {"ok": False, "message": str(e)}

    pending = get_pending_uploads(limit=max_items)
    synced = 0
    failed = 0

    for q in pending:
        pdf_path = q["file_path"]
        if not os.path.exists(pdf_path):
            logging.warning(f"Pending PDF missing, marking FAILED: {pdf_path}")
            mark_failed(q["id"])
            failed += 1
            continue

        file_name = os.path.basename(pdf_path)
        bill_number = os.path.splitext(file_name)[0]
        year = str(bill_number).split("-")[0] if "-" in bill_number else "Unknown"

        try:
            year_id = get_or_create_year_folder(service, root_id, year)
            upload_pdf(service, year_id, pdf_path, file_name)
            mark_synced(q["id"])
            synced += 1
        except Exception as e:
            logging.warning(f"Failed to sync pending {file_name}: {e}")
            failed += 1
            continue

    logging.info(f"Drive sync checked {len(pending)}, synced {synced}, failed {failed}")
    return {"ok": True, "synced": synced, "failed": failed, "pending_checked": len(pending)}

def sync_pending_in_background():
    global _sync_running
    with _sync_lock:
        if _sync_running:
            logging.debug("Sync already running, skip")
            return
        _sync_running = True

    def worker():
        global _sync_running
        try:
            logging.info("Starting background Drive sync")
            result = sync_pending_uploads()
            logging.info(f"Background sync result: {result}")
        except Exception as e:
            logging.error(f"Background sync error: {e}")
        finally:
            with _sync_lock:
                _sync_running = False

    t = threading.Thread(target=worker, daemon=True, name="DriveSync")
    t.start()
