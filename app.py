"""
NutriCoach T2D - local server + desktop app shell (standard library only).

Modes:
  * python app.py            -> classic console server (development / start.bat)
  * NutriCoach.exe           -> desktop app: opens its own app window (Edge/Chrome
                                app mode - no tabs, no address bar, no console)
                                and shuts itself down after the window closes.
  * NUTRICOACH_WINDOW=0      -> headless server (used by the automated tests)

Endpoints:
  GET  /                     chat UI (web/index.html)
  GET  /api/foods?lang=de    localized food knowledge base for the side panel
  GET  /api/ping             heartbeat from the UI (drives auto-shutdown)
  POST /api/chat             {"message": "...", "lang": "en"|"de"} -> engine response

Privacy: everything runs locally. Messages are appended to data/logs/*.jsonl
on this machine only (useful for usage analysis in the research project);
delete the folder or set NUTRICOACH_LOG=0 to disable.
"""

import json
import os
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

APP_VERSION = "1.0.1"
FROZEN = getattr(sys, "frozen", False)  # True when running as NutriCoach.exe

# In windowed (no-console) builds stdout/stderr are None - keep print() safe.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Read-only resources (knowledge base, UI): unpacked to sys._MEIPASS in the exe.
RESOURCE_DIR = sys._MEIPASS if FROZEN else os.path.dirname(os.path.abspath(__file__))
# Writable location (chat logs, error log): next to the exe / the project folder.
APP_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, RESOURCE_DIR)

from chatbot.engine import ChatEngine  # noqa: E402

PORT = int(os.environ.get("PORT", "8765"))
LOG_ENABLED = os.environ.get("NUTRICOACH_LOG", "1") != "0"
LOG_DIR = os.path.join(APP_DIR, "data", "logs")

# Watchdog: the UI pings /api/ping; once the last window/tab is gone, requests
# stop and the app exits on its own (relevant for the windowed exe).
LAST_REQUEST = [time.time()]
IDLE_EXIT_SECONDS = 120

engine = ChatEngine(data_dir=os.path.join(RESOURCE_DIR, "data"))

with open(os.path.join(RESOURCE_DIR, "web", "index.html"), encoding="utf-8") as f:
    INDEX_HTML = f.read().encode("utf-8")


def log_turn(message: str, intent: str, lang: str) -> None:
    if not LOG_ENABLED:
        return
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, f"chat-{datetime.now():%Y-%m-%d}.jsonl")
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "message": message, "intent": intent, "lang": lang}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # logging must never break the chat


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        LAST_REQUEST[0] = time.time()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj, status: int = 200) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML, "text/html; charset=utf-8")
        elif parsed.path == "/api/foods":
            lang = (parse_qs(parsed.query).get("lang", ["en"])[0] or "en")[:2]
            self._send_json({"foods": engine.food_list(lang)})
        elif parsed.path == "/api/ping":
            self._send_json({"ok": True, "version": APP_VERSION})
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat":
            self._send(404, b"Not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            message = str(payload.get("message", ""))[:500]
            lang = str(payload.get("lang", "en"))[:2]
        except (ValueError, json.JSONDecodeError):
            self._send_json({"error": "invalid request"}, status=400)
            return
        response = engine.reply(message, lang)
        log_turn(message, response["intent"], response["lang"])
        self._send_json(response)

    def log_message(self, fmt, *args):  # keep the console readable
        if "/api/chat" in (args[0] if args else ""):
            print(f"[chat] {self.address_string()} {args[0]}")


def make_server():
    """Bind the first free port starting at PORT (handy for double-click users)."""
    last_err = None
    for port in range(PORT, PORT + 10):
        try:
            return ThreadingHTTPServer(("127.0.0.1", port), Handler), port
        except OSError as err:
            last_err = err
    raise SystemExit(f"No free port between {PORT} and {PORT + 9}: {last_err}")


def find_app_browser():
    """A browser that supports app mode (own window, no tabs/address bar)."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def alert(text: str, title: str = "NutriCoach T2D") -> None:
    """Show a message box. In a windowed build there is no console, so this is
    the only way the user ever learns that something went wrong."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)  # MB_ICONINFORMATION
    except Exception:
        print(f"{title}: {text}")


def close_splash() -> None:
    """Dismiss the PyInstaller splash screen (only present in the frozen build)."""
    try:
        import pyi_splash  # type: ignore
        pyi_splash.close()
    except Exception:
        pass


def open_window(url: str) -> bool:
    """Open the app in its own window; fall back to the default browser."""
    browser = find_app_browser()
    if browser:
        try:
            subprocess.Popen([browser, f"--app={url}", "--window-size=1180,820"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            pass  # fall through to the default browser
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def already_running(port: int) -> bool:
    """True if another NutriCoach instance already serves this port."""
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            return json.loads(r.read().decode("utf-8")).get("ok") is True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def run_windowed(server, url: str) -> None:
    """Desktop-app experience: app window + auto-shutdown once it is closed."""
    threading.Thread(target=server.serve_forever, daemon=True).start()
    opened = open_window(url)
    close_splash()
    if not opened:
        alert("NutriCoach could not open a window automatically.\n\n"
              f"Please open this address in your web browser:\n{url}\n\n"
              "The app keeps running until you close this message.")
    # The UI pings /api/ping while at least one window shows the app.
    # When pings stop (window closed), shut down quietly.
    try:
        while time.time() - LAST_REQUEST[0] < IDLE_EXIT_SECONDS:
            time.sleep(10)
    except KeyboardInterrupt:
        pass
    server.shutdown()


def main():
    windowed = FROZEN and os.environ.get("NUTRICOACH_WINDOW", "1") != "0"

    # Double-clicked twice? Just show the window of the instance already running.
    if windowed and already_running(PORT):
        open_window(f"http://localhost:{PORT}")
        close_splash()
        return

    server, port = make_server()
    url = f"http://localhost:{port}"
    print("=" * 56)
    print(f"  NutriCoach T2D v{APP_VERSION} - research prototype")
    print(f"  Open:  {url}")
    print("  Stop:  Ctrl+C or close this window   (local only)")
    print("=" * 56)

    if windowed:
        run_windowed(server, url)
        return

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # No console in the windowed exe - never fail silently: write a note and
        # tell the user on screen, otherwise "nothing happens" is all they see.
        details = traceback.format_exc()
        log_path = os.path.join(APP_DIR, "error.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.now().isoformat(timespec='seconds')} ---\n")
                f.write(details)
        except OSError:
            log_path = "(could not be written)"
        try:
            close_splash()
        except Exception:
            pass
        alert("NutriCoach could not start.\n\n"
              f"{details.strip().splitlines()[-1]}\n\n"
              f"Details were saved to:\n{log_path}", "NutriCoach T2D - error")
        raise
