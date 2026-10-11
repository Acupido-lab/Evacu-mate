"""
EvacuMate - Permanent Public Online Runtime Gateway Supervisor
--------------------------------------------------------------
Guarantees a single, fixed, permanent public URL that NEVER changes and NEVER expires.
Enforces:
  1. Binding to ONE permanent reserved domain only.
  2. Preserving the exact same URL across restarts, reboots, and updates.
  3. No random subdomains / no temporary links.
  4. Auto-reconnect supervisor loop with exponential backoff.
  5. Full global public internet accessibility.
  6. HTTPS enabled by default.
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
NGROK_ZIP_URL = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [{level}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def update_status(status, public_url=None, error=None):
    payload = {
        "status": status,
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

def load_config():
    if not os.path.exists(CONFIG_FILE):
        log(f"Configuration file not found at: {CONFIG_FILE}", "ERROR")
        log("Creating default gateway_config.json template...", "INFO")
        default_cfg = {
            "_comment": "EvacuMate Permanent Public Online Runtime Gateway Configuration",
            "permanent_domain": "YOUR_RESERVED_DOMAIN.ngrok-free.app",
            "authtoken": "",
            "port": 8550,
            "auto_reconnect": True,
            "reconnect_delay_seconds": 5,
            "bind_tls": True
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
        return default_cfg

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to parse config file: {e}", "ERROR")
        return {}

def ensure_ngrok_binary():
    # 1. Check local bin/
    if os.path.isfile(NGROK_EXE):
        return NGROK_EXE

    # 2. Check root directory
    root_ngrok = os.path.join(PROJECT_DIR, "ngrok.exe")
    if os.path.isfile(root_ngrok):
        return root_ngrok

    # 3. Check system PATH
    try:
        result = subprocess.run(["where", "ngrok"], capture_output=True, text=True)
        if result.returncode == 0:
            found = result.stdout.strip().splitlines()[0]
            if os.path.isfile(found):
                return found
    except Exception:
        pass

    # 4. Download and extract ngrok automatically
    log("Ngrok binary not found. Downloading official Windows binary...", "INFO")
    os.makedirs(BIN_DIR, exist_ok=True)
    zip_dest = os.path.join(BIN_DIR, "ngrok.zip")

    try:
        urllib.request.urlretrieve(NGROK_ZIP_URL, zip_dest)
        log("Extracting ngrok.zip...", "INFO")
        import zipfile
        with zipfile.ZipFile(zip_dest, 'r') as zf:
            zf.extractall(BIN_DIR)
        if os.path.exists(zip_dest):
            os.remove(zip_dest)
        if os.path.isfile(NGROK_EXE):
            log("Ngrok installed successfully to bin/ngrok.exe", "INFO")
            return NGROK_EXE
    except Exception as e:
        log(f"Failed to auto-download ngrok: {e}", "ERROR")
        raise RuntimeError(f"Could not locate or download ngrok: {e}")

    raise RuntimeError("Ngrok binary could not be found.")

def is_port_open(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex((host, port)) == 0

def configure_authtoken(ngrok_bin, token):
    if not token or token.startswith("YOUR_") or token.strip() == "":
        return
    log("Registering Ngrok authtoken...", "INFO")
    try:
        res = subprocess.run([ngrok_bin, "config", "add-authtoken", token.strip()], capture_output=True, text=True)
        if res.returncode == 0:
            log("Ngrok authtoken configured successfully.", "INFO")
        else:
            log(f"Ngrok authtoken warning: {res.stderr.strip()}", "WARNING")
    except Exception as e:
        log(f"Error configuring authtoken: {e}", "ERROR")

def start_backend_server_if_needed(port=8550):
    if is_port_open(port):
        log(f"Backend EvacuMate server is already running on port {port}.", "INFO")
        return None

    log(f"Starting backend EvacuMate server on port {port}...", "INFO")
    
    # Check for python executable (virtual env or system)
    venv_python = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
    python_cmd = venv_python if os.path.isfile(venv_python) else sys.executable

    env = os.environ.copy()
    env["PORT"] = str(port)
    env["NO_BROWSER"] = "1"  # Do not auto-launch browser on background gateway startup

    main_script = os.path.join(PROJECT_DIR, "main.py")
    proc = subprocess.Popen(
        [python_cmd, main_script],
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait up to 10 seconds for backend to start
    for _ in range(20):
        time.sleep(0.5)
        if is_port_open(port):
            log(f"Backend EvacuMate server successfully started (PID: {proc.pid}).", "INFO")
            return proc

    log("Warning: Backend server started but port check timed out.", "WARNING")
    return proc

def query_ngrok_public_url():
    """Polls ngrok internal inspect API to obtain the active public tunnel URL."""
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            tunnels = data.get("tunnels", [])
            for t in tunnels:
                url = t.get("public_url", "")
                if url.startswith("https://"):
                    return url
            if tunnels:
                return tunnels[0].get("public_url")
    except Exception:
        pass
    return None

def kill_existing_ngrok():
    """Kills any orphaned ngrok process to prevent ERR_NGROK_334 endpoint collision."""
    try:
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "ngrok"], capture_output=True)
        time.sleep(0.5)
    except Exception:
        pass

def run_gateway():
    log("==========================================================", "INFO")
    log("  EvacuMate Permanent Public Online Runtime Gateway      ", "INFO")
    log("==========================================================", "INFO")

    update_status("initializing")
    cfg = load_config()
    permanent_domain = cfg.get("permanent_domain", "").strip()
    authtoken = cfg.get("authtoken", "").strip()
    port = int(cfg.get("port", 8550))
    auto_reconnect = bool(cfg.get("auto_reconnect", True))
    reconnect_delay = int(cfg.get("reconnect_delay_seconds", 5))

    # Strip prefixes if entered by mistake
    if permanent_domain.startswith("https://"):
        permanent_domain = permanent_domain[8:]
    elif permanent_domain.startswith("http://"):
        permanent_domain = permanent_domain[7:]
    permanent_domain = permanent_domain.strip().rstrip("/")

    # RULE 1 & 3: Bind to ONE permanent reserved domain only. No random subdomains.
    if not permanent_domain or "YOUR_" in permanent_domain.upper():
        err_msg = (
            "PERMANENT DOMAIN REQUIRED: You must specify your reserved domain in gateway_config.json.\n"
            "Example: 'permanent_domain': 'extended-unshackle-evoke.ngrok-free.dev'\n"
            "Random subdomains are strictly disallowed per Gateway rules."
        )
        log(err_msg, "ERROR")
        update_status("error", error=err_msg)
        print("\nTo configure your permanent domain, edit gateway_config.json or run configure_gateway.bat\n")
        return 1

    # Check Authtoken
    if not authtoken or "YOUR_" in authtoken.upper():
        log("NOTICE: Ngrok authtoken not set in gateway_config.json.", "WARNING")
        log("If ngrok is not authenticated, static domains will be rejected by ngrok.", "WARNING")
        log("Get your free authtoken at: https://dashboard.ngrok.com/get-started/your-authtoken", "WARNING")

    ngrok_bin = ensure_ngrok_binary()
    if authtoken and "YOUR_" not in authtoken.upper():
        configure_authtoken(ngrok_bin, authtoken)

    expected_url = f"https://{permanent_domain}"
    log(f"Target Permanent Public URL : {expected_url}", "INFO")
    log(f"Binding Local Port         : {port}", "INFO")
    log(f"Gateway Auto-Reconnect     : {'ENABLED (Resilient 24/7)' if auto_reconnect else 'DISABLED'}", "INFO")

    backend_proc = None
    ngrok_proc = None

    def cleanup(signum=None, frame=None):
        log("Shutting down Permanent Gateway...", "INFO")
        update_status("stopped")
        if ngrok_proc and ngrok_proc.poll() is None:
            try:
                ngrok_proc.terminate()
            except Exception:
                pass
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

    consecutive_failures = 0

    while True:
        try:
            # 1. Ensure backend Flask server is alive
            if not is_port_open(port):
                backend_proc = start_backend_server_if_needed(port)

            # 2. Kill any orphaned ngrok process before starting to prevent endpoint conflict
            kill_existing_ngrok()

            # 3. Start ngrok bound strictly to the permanent domain
            cmd = [
                ngrok_bin,
                "http",
                f"--url=https://{permanent_domain}",
                "--host-header=rewrite",
                f"127.0.0.1:{port}",
                "--log=stdout",
                "--log-format=term"
            ]

            log(f"Connecting tunnel to permanent public link: {expected_url} ...", "INFO")
            ngrok_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Wait 2 seconds for tunnel to establish
            time.sleep(2)

            if ngrok_proc.poll() is None:
                active_url = expected_url
                log("==========================================================", "INFO")
                log(f" [ONLINE] PERMANENT PUBLIC ONLINE GATEWAY ACTIVE!", "INFO")
                log(f" Public URL : {active_url}", "INFO")
                log(f" Local URL  : http://127.0.0.1:{port}", "INFO")
                log(f" Access     : Global Public Internet (Any gadget anywhere)", "INFO")
                log(f" Security   : Enforced HTTPS & Active SSL Certificate", "INFO")
                log("==========================================================", "INFO")
                update_status("online", public_url=active_url)
                consecutive_failures = 0

                # Auto-open browser directly to the permanent public link!
                if os.environ.get('NO_BROWSER') is None:
                    try:
                        import webbrowser
                        webbrowser.open(active_url)
                    except Exception:
                        pass
            else:
                out = ngrok_proc.stdout.read() if ngrok_proc.stdout else ""
                log(f"Ngrok connection error: {out[:300]}", "ERROR")
                update_status("error", error=out[:300])

            # 4. Monitor loop: Keep tunnel alive 24/7
            while True:
                time.sleep(3)
                poll = ngrok_proc.poll()
                if poll is not None:
                    # ngrok process exited unexpectedly
                    stdout_tail = ""
                    try:
                        stdout_tail = ngrok_proc.stdout.read()
                    except Exception:
                        pass
                    log(f"Ngrok tunnel process exited (code {poll}). Output: {stdout_tail[:300]}", "WARNING")
                    update_status("disconnected", error=f"Ngrok exited with code {poll}")
                    break

                # Periodic health check of tunnel
                current_url = query_ngrok_public_url()
                if not current_url:
                    log("Health check: Tunnel API not responding, checking connectivity...", "WARNING")
                else:
                    update_status("online", public_url=current_url)

        except Exception as e:
            log(f"Gateway supervisor error: {e}", "ERROR")
            update_status("error", error=str(e))

        if not auto_reconnect:
            log("Auto-reconnect is disabled. Exiting gateway.", "INFO")
            break

        consecutive_failures += 1
        wait_seconds = min(reconnect_delay * consecutive_failures, 60)
        log(f"Reconnecting to permanent domain in {wait_seconds} seconds (Attempt {consecutive_failures})...", "INFO")
        time.sleep(wait_seconds)

if __name__ == "__main__":
    sys.exit(run_gateway() or 0)
