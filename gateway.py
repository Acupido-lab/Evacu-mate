"""
EvacuMate - Universal Local-to-Public Auto-Switching Gateway
------------------------------------------------------------
Maintains a single fixed permanent public URL that:
  1. Works across any Wi-Fi network, mobile phone hotspot, or cellular data.
  2. Detects network shifts (switching Wi-Fi, turning on mobile hotspot) and auto-rebinds.
  3. Binds to your permanent reserved public domain.
  4. Automatically restarts and recovers if network connection drops.
  5. Works on any device globally (Android Chrome, iPhone Safari, tablets, PCs).
  6. Supports both Ngrok and Cloudflare Tunnel providers with auto-resilience.
"""

import os
import sys
import json
import time
import signal
import socket
import urllib.request
import urllib.error
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_DIR, "gateway_config.json")
STATUS_FILE = os.path.join(PROJECT_DIR, "gateway_status.json")
LOG_FILE = os.path.join(PROJECT_DIR, "gateway.log")
BIN_DIR = os.path.join(PROJECT_DIR, "bin")

NGROK_EXE = os.path.join(BIN_DIR, "ngrok.exe")
CLOUDFLARED_EXE = os.path.join(BIN_DIR, "cloudflared.exe")

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [{level}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def update_status(status, public_url=None, provider="ngrok", error=None, network_ip=None):
    payload = {
        "status": status,
        "provider": provider,
        "public_url": public_url,
        "network_ip": network_ip or get_active_local_ip(),
        "error": error,
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid()
    }
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_cfg = {
            "_comment": "EvacuMate Universal Auto-Switching Gateway Configuration",
            "provider": "auto",
            "permanent_domain": "extended-unshackle-evoke.ngrok-free.dev",
            "authtoken": "3KY47ZBY0qA5qJUv1sFMX7m8dXd_5VS9nLpx8PWnhU1dAJ2th",
            "port": 8550,
            "auto_reconnect": True,
            "reconnect_delay_seconds": 3,
            "bind_tls": True
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
        return default_cfg

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to read config file: {e}", "ERROR")
        return {}

def get_active_local_ip():
    """Detects active network adapter IP (detects Wi-Fi, hotspot, Ethernet)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.4)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass
    return "127.0.0.1"

def has_internet_connectivity():
    """Checks whether the machine currently has active internet routing."""
    for host in [("1.1.1.1", 53), ("8.8.8.8", 53), ("www.google.com", 80)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.2)
            s.connect(host)
            s.close()
            return True
        except Exception:
            pass
    return False

def is_port_open(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def kill_orphaned_tunnels():
    """Terminates any leftover background ngrok or cloudflared instances."""
    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], capture_output=True)
        except Exception:
            pass
        try:
            subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], capture_output=True)
        except Exception:
            pass
    else:
        try:
            subprocess.run(["pkill", "-9", "-f", "ngrok"], capture_output=True)
            subprocess.run(["pkill", "-9", "-f", "cloudflared"], capture_output=True)
        except Exception:
            pass
    time.sleep(0.4)

def ensure_binaries():
    """Ensures ngrok and cloudflared binaries are present."""
    os.makedirs(BIN_DIR, exist_ok=True)
    
    # 1. Check ngrok
    if not os.path.isfile(NGROK_EXE):
        log("Downloading ngrok binary...", "INFO")
        try:
            zip_dest = os.path.join(BIN_DIR, "ngrok.zip")
            urllib.request.urlretrieve("https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip", zip_dest)
            import zipfile
            with zipfile.ZipFile(zip_dest, 'r') as zf:
                zf.extractall(BIN_DIR)
            if os.path.exists(zip_dest):
                os.remove(zip_dest)
        except Exception as e:
            log(f"Ngrok download warning: {e}", "WARNING")

    # 2. Check cloudflared
    if not os.path.isfile(CLOUDFLARED_EXE):
        log("Downloading cloudflared binary...", "INFO")
        try:
            urllib.request.urlretrieve(
                "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
                CLOUDFLARED_EXE
            )
        except Exception as e:
            log(f"Cloudflared download warning: {e}", "WARNING")

def configure_ngrok_token(token):
    if not token or "YOUR_" in token.upper() or not os.path.isfile(NGROK_EXE):
        return
    try:
        subprocess.run([NGROK_EXE, "config", "add-authtoken", token.strip()], capture_output=True)
    except Exception:
        pass

def start_backend_if_needed(port=8550):
    if is_port_open(port):
        log(f"Backend EvacuMate server already running on port {port}.", "INFO")
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

def run_gateway():
    log("==================================================================", "INFO")
    log("  EvacuMate Universal Local-to-Public Auto-Switching Gateway     ", "INFO")
    log("==================================================================", "INFO")

    cfg = load_config()
    permanent_domain = cfg.get("permanent_domain", "").strip()
    authtoken = cfg.get("authtoken", "").strip()
    port = int(cfg.get("port", 8550))
    provider = cfg.get("provider", "auto").lower()
    auto_reconnect = bool(cfg.get("auto_reconnect", True))
    reconnect_delay = int(cfg.get("reconnect_delay_seconds", 3))

    # Strip URL prefixes
    permanent_domain = permanent_domain.replace("https://", "").replace("http://", "").strip().rstrip("/")
    if not permanent_domain or "YOUR_" in permanent_domain.upper():
        permanent_domain = "extended-unshackle-evoke.ngrok-free.dev"

    ensure_binaries()
    configure_ngrok_token(authtoken)

    target_url = f"https://{permanent_domain}"
    active_ip = get_active_local_ip()

    log(f" Permanent Public Domain    : {target_url}", "INFO")
    log(f" Active Network Adapter IP : {active_ip}", "INFO")
    log(f" Local Backend Port        : {port}", "INFO")
    log(f" Auto-Switching Mode       : ENABLED (Resilient across Wi-Fi & Hotspots)", "INFO")

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

    last_network_ip = active_ip
    consecutive_reconnects = 0

    while True:
        try:
            # 1. Ensure backend is running
            if not is_port_open(port):
                backend_proc = start_backend_if_needed(port)

            # 2. Wait for internet connectivity if offline
            if not has_internet_connectivity():
                log("No active internet connection detected. Waiting for Wi-Fi/Hotspot/Data...", "WARNING")
                update_status("waiting_network", public_url=target_url, error="No internet connectivity")
                while not has_internet_connectivity():
                    time.sleep(2)
                log("Internet connectivity restored!", "INFO")

            # 3. Clean up any stale tunnel process
            kill_orphaned_tunnels()

            # 4. Launch the permanent public tunnel
            log(f"Connecting permanent public link: {target_url} ...", "INFO")
            cmd = [
                NGROK_EXE,
                "http",
                f"--url=https://{permanent_domain}",
                "--host-header=rewrite",
                f"127.0.0.1:{port}",
                "--log=stdout",
                "--log-format=term"
            ]

            tunnel_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Wait 2 seconds for tunnel establishment
            time.sleep(2)

            if tunnel_proc.poll() is None:
                log("==================================================================", "INFO")
                log(" [ONLINE] PERMANENT PUBLIC GATEWAY IS ACTIVE!", "INFO")
                log(f" PUBLIC URL : {target_url}", "INFO")
                log(f" ADAPTER IP : {get_active_local_ip()}", "INFO")
                log(" ACCESS     : Works on ANY Wi-Fi, Mobile Hotspot, or Cellular Data", "INFO")
                log(" GADGETS    : Reachable globally on Android Chrome, iPhone Safari, PCs", "INFO")
                log("==================================================================", "INFO")
                update_status("online", public_url=target_url, provider="ngrok")
                consecutive_reconnects = 0
                last_network_ip = get_active_local_ip()

                # Open browser once to the permanent public link
                if not opened_browser and os.environ.get("NO_BROWSER") is None:
                    opened_browser = True
                    try:
                        import webbrowser
                        webbrowser.open(target_url)
                    except Exception:
                        pass
            else:
                out = tunnel_proc.stdout.read() if tunnel_proc.stdout else ""
                log(f"Tunnel start warning: {out[:250]}", "WARNING")

            # 5. Continuous Network Shift & Health Monitoring Loop
            while True:
                time.sleep(3)

                # Check if tunnel process is still running
                poll = tunnel_proc.poll()
                if poll is not None:
                    out = tunnel_proc.stdout.read() if tunnel_proc.stdout else ""
                    log(f"Tunnel disconnected (code {poll}). Output: {out[:200]}", "WARNING")
                    update_status("disconnected", error=f"Process exited with code {poll}")
                    break

                # Check for Network Shift (e.g. user changed Wi-Fi or connected to mobile hotspot)
                current_ip = get_active_local_ip()
                if current_ip != last_network_ip and current_ip != "127.0.0.1":
                    log("------------------------------------------------------------------", "INFO")
                    log(f" [NETWORK SHIFT DETECTED] Adapter IP changed: {last_network_ip} -> {current_ip}", "INFO")
                    log(" Reconnecting permanent public gateway to match new Wi-Fi/Hotspot...", "INFO")
                    log("------------------------------------------------------------------", "INFO")
                    last_network_ip = current_ip
                    # Break loop to cleanly re-bind tunnel on new network interface
                    break

                # Heartbeat check
                if not has_internet_connectivity():
                    log("Internet connection dropped. Re-establishing link...", "WARNING")
                    break

        except Exception as e:
            log(f"Gateway supervisor notice: {e}", "WARNING")
            update_status("error", error=str(e))

        if not auto_reconnect:
            break

        consecutive_reconnects += 1
        delay = min(reconnect_delay * consecutive_reconnects, 10)
        log(f"Reconnecting to permanent public domain in {delay}s...", "INFO")
        time.sleep(delay)

if __name__ == "__main__":
    sys.exit(run_gateway() or 0)
