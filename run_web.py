"""
Launch the Laxmi Electricals Billing mobile web server.

Usage:
    python run_web.py                 # http://0.0.0.0:8000
    python run_web.py --port 9000

Then open the shown LAN address on any phone connected to the same Wi-Fi.
"""
import argparse
import socket
import uvicorn


def lan_ip() -> str:
    """Best-effort LAN IP so the owner knows what to type on the phone."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true")
    a = ap.parse_args()

    print("\n" + "=" * 54)
    print("  Laxmi Electricals Billing — Mobile Web Edition")
    print("=" * 54)
    print(f"  On this computer : http://localhost:{a.port}")
    print(f"  On your phone    : http://{lan_ip()}:{a.port}")
    print("  (phone must be on the same Wi-Fi network)")
    print("=" * 54 + "\n")

    uvicorn.run("web.app:app", host=a.host, port=a.port, reload=a.reload)
