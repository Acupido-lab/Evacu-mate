"""
EvacuMate - Public Online Gateway (Multi-Network & Mobile Data Ready)
--------------------------------------------------------------------
Provides a public URL that:
  1. Can be accessed from DIFFERENT devices on DIFFERENT Wi-Fi networks or mobile cellular data.
  2. Does NOT require devices to be on the same Wi-Fi.
  3. Has ZERO warning screens (Cloudflare Global Edge).
  4. Automatically copies the active public link to clipboard.
  5. Automatically opens the public link in your browser.
"""

import os
import sys
import json
import time
import signal
import socket
import re
import urllib.request
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_DIR, "gateway_config.json")
STATUS_FILE = os.path.join(PROJECT_DIR, "gateway_status.json")
LOG_FILE = os.path.join(PROJECT_DIR, "gateway.log")
BIN_DIR = os.path.join(PROJECT_DIR, "bin")

CLOUDFLARED_EXE = os.path.join(BIN_DIR, "cloudflared.exe")
NGROK_EXE = os.path.join(BIN_DIR, "ngrok.exe")

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [{level}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def update_status(status, public_url=None, provider="cloudflare", error=None):
    payload = {
        "status": status,
        "provider": provider,
        "public_url": public_url,
        "error": error,
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid()
    }
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

def copy_to_clipboard(text):
    if not text:
        return
    try:
        if os.name == 'nt':
            cmd = f"Set-Clipboard -Value '{text}'"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=3)
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_cfg = {
            "provider": "cloudflare",
            "permanent_domain": "extended-unshackle-evoke.ngrok-free.dev",
            "authtoken": "3KY47ZBY0qA5qJUv1sFMX7m8dXd_5VS9nLpx8PWnhU1dAJ2th",
            "port": 8550,
            "auto_reconnect": True
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
        return default_cfg

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def is_port_open(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def kill_orphaned_tunnels():
    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], capture_output=True)
        except Exception:
            pass
        try:
            subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], capture_output=True)
        except Exception:
            pass
    else:
        try:
            subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)
            subprocess.run(["pkill", "-f", "ngrok"], capture_output=True)
        except Exception:
            pass
    time.sleep(0.3)

def ensure_binaries():
    os.makedirs(BIN_DIR, exist_ok=True)
    if not os.path.isfile(CLOUDFLARED_EXE):
        log("Downloading Cloudflare Tunnel binary...", "INFO")
        try:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            urllib.request.urlretrieve(url, CLOUDFLARED_EXE)
        except Exception as e:
            log(f"Cloudflared download error: {e}", "ERROR")

    if not os.path.isfile(NGROK_EXE):
        try:
            zip_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
            zip_dest = os.path.join(BIN_DIR, "ngrok.zip")
            urllib.request.urlretrieve(zip_url, zip_dest)
            import zipfile
            with zipfile.ZipFile(zip_dest, 'r') as zf:
                zf.extractall(BIN_DIR)
            if os.path.exists(zip_dest):
                os.remove(zip_dest)
        except Exception:
            pass

def start_backend_server(port=8550):
    if is_port_open(port):
        log(f"Backend EvacuMate server is already running on port {port}.", "INFO")
        return None

    log(f"Starting backend EvacuMate server on port {port}...", "INFO")
    python_cmd = sys.executable
    venv_py = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
    if os.path.isfile(venv_py):
        python_cmd = venv_py

    env = os.environ.copy()
    env["PORT"] = str(port)
    env["NO_BROWSER"] = "1"

    main_script = os.path.join(PROJECT_DIR, "main.py")
    proc = subprocess.Popen(
        [python_cmd, main_script],
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    for _ in range(25):
        time.sleep(0.4)
        if is_port_open(port):
            log(f"Backend server active on port {port} (PID: {proc.pid}).", "INFO")
            return proc

    return proc

def run_cloudflare_tunnel(port=8550):
    """Starts Cloudflare Tunnel, extracts the public URL, and monitors it."""
    import threading
    cmd = [CLOUDFLARED_EXE, "tunnel", "--url", f"http://127.0.0.1:{port}"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    url_event = threading.Event()
    holder = {"url": None}

    def reader():
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                if not holder["url"]:
                    m = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', line)
                    if m:
                        holder["url"] = m.group(0)
                        url_event.set()
        except Exception:
            pass

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    # Wait up to 20 seconds for the public trycloudflare URL to be created
    url_event.wait(timeout=20)
    return proc, holder["url"]

def run_ngrok_tunnel(domain, port=8550):
    """Starts Ngrok bound to permanent domain."""
    import threading
    cmd = [
        NGROK_EXE,
        "http",
        f"--url=https://{domain}",
        "--host-header=rewrite",
        f"127.0.0.1:{port}",
        "--log=stdout"
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def reader():
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
        except Exception:
            pass

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    time.sleep(2.5)
    if proc.poll() is None:
        return proc, f"https://{domain}"
    return proc, None

def print_banner(public_url, provider):
    border = "=" * 70
    print("\n" + border, flush=True)
    print("      EVACUMATE PUBLIC ONLINE ACCESS (SHARE WITH ANYONE)", flush=True)
    print(border, flush=True)
    print(f"\n  PUBLIC URL : {public_url}\n", flush=True)
    print("  DIFFERENT WI-FI & MOBILE DATA READY:", flush=True)
    print("   * People on DIFFERENT Wi-Fi networks can open this link!", flush=True)
    print("   * People on Mobile Cellular Data (4G / 5G) can open this link!", flush=True)
    print("   * Works on any phone, tablet, iPhone, Android, Mac, or PC!", flush=True)
    print("   * Zero warning screen - loads directly in Google Chrome & Safari!", flush=True)
    print(f"\n  [COPIED] Link copied to your clipboard! Just press Ctrl+V to share.", flush=True)
    print(border + "\n", flush=True)

def run_gateway():
    log("==================================================================", "INFO")
    log("    EvacuMate Public Online Runtime Gateway (Global Access)       ", "INFO")
    log("==================================================================", "INFO")

    cfg = load_config()
    provider = cfg.get("provider", "cloudflare").lower()
    permanent_domain = cfg.get("permanent_domain", "extended-unshackle-evoke.ngrok-free.dev").strip()
    port = int(cfg.get("port", 8550))
    auto_reconnect = bool(cfg.get("auto_reconnect", True))

    ensure_binaries()
    backend_proc = None
    tunnel_proc = None
    opened_browser = False

    def cleanup(signum=None, frame=None):
        log("Shutting down Gateway...", "INFO")
        update_status("stopped")
        kill_orphaned_tunnels()
        if backend_proc and backend_proc.poll() is None:
            try:
                backend_proc.terminate()
            except Exception:
                pass
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
    except Exception:
        pass

    while True:
        try:
            # 1. Ensure backend server is running
            if not is_port_open(port):
                backend_proc = start_backend_server(port)

            # 2. Kill leftover tunnels to prevent port or tunnel collisions
            kill_orphaned_tunnels()

            # 3. Launch tunnel (Cloudflare by default for 100% warning-free multi-network access)
            public_url = None
            if provider == "cloudflare":
                log("Starting Cloudflare Global Edge Tunnel...", "INFO")
                tunnel_proc, public_url = run_cloudflare_tunnel(port)
            else:
                log(f"Starting Ngrok Tunnel to permanent domain {permanent_domain}...", "INFO")
                tunnel_proc, public_url = run_ngrok_tunnel(permanent_domain, port)

            if public_url:
                update_status("online", public_url=public_url, provider=provider)
                copy_to_clipboard(public_url)
                print_banner(public_url, provider)

                # Open browser once
                if not opened_browser and os.environ.get("NO_BROWSER") is None:
                    opened_browser = True
                    try:
                        import webbrowser
                        time.sleep(1.0)
                        webbrowser.open(public_url)
                    except Exception:
                        pass
            else:
                log("Failed to establish public tunnel URL. Retrying...", "WARNING")

            # 4. Monitor loop
            while True:
                time.sleep(3)
                poll = tunnel_proc.poll()
                if poll is not None:
                    log(f"Tunnel disconnected (exit code {poll}). Re-connecting...", "WARNING")
                    update_status("disconnected", error=f"Exit code {poll}")
                    break

        except Exception as e:
            log(f"Gateway supervisor notice: {e}", "WARNING")
            update_status("error", error=str(e))

        if not auto_reconnect:
            break

        time.sleep(3)

if __name__ == "__main__":
    sys.exit(run_gateway() or 0)
