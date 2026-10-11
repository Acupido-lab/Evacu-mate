"""
EvacuMate - Gateway Configuration & Management Utility
"""

import os
import sys
import json
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_DIR, "gateway_config.json")
STATUS_FILE = os.path.join(PROJECT_DIR, "gateway_status.json")
LOG_FILE = os.path.join(PROJECT_DIR, "gateway.log")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "permanent_domain": "",
            "authtoken": "",
            "port": 8550,
            "auto_reconnect": True,
            "reconnect_delay_seconds": 5,
            "bind_tls": True
        }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print("\n [SUCCESS] Configuration saved to gateway_config.json!\n")
    except Exception as e:
        print(f"\n [ERROR] Could not save config: {e}\n")

def show_status():
    print("\n--------------------------------------------------------------")
    print(" GATEWAY STATUS & LOGS")
    print("--------------------------------------------------------------")
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f" Status     : {data.get('status', 'unknown').upper()}")
                print(f" Public URL : {data.get('public_url', 'None')}")
                if data.get('error'):
                    print(f" Error      : {data.get('error')}")
                print(f" Last Event : {data.get('timestamp', 'unknown')}")
        except Exception:
            print(" Status file could not be read.")
    else:
        print(" Gateway has not been run yet.")

    print("\n Recent Logs (Last 10 lines):")
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print("  " + line.strip())
        except Exception:
            pass
    else:
        print("  (No log file found)")
    print("--------------------------------------------------------------\n")

def main():
    while True:
        cfg = load_config()
        current_domain = cfg.get("permanent_domain", "") or "(Not set)"
        current_token = cfg.get("authtoken", "")
        masked_token = f"{current_token[:6]}...{current_token[-4:]}" if len(current_token) > 10 else ("(Not set)" if not current_token else "(Set)")

        print("==============================================================")
        print("   EvacuMate Permanent Public Online Runtime Gateway Setup   ")
        print("==============================================================")
        print(f" 1. Permanent Domain : {current_domain}")
        print(f" 2. Ngrok Authtoken  : {masked_token}")
        print(f" 3. Target Port      : {cfg.get('port', 8550)}")
        print("--------------------------------------------------------------")
        print(" [1] Set / Change Permanent Reserved Domain")
        print(" [2] Set / Change Ngrok Authtoken")
        print(" [3] Test & Run Gateway in Foreground (Live Output)")
        print(" [4] Install Auto-Reconnect on Windows Boot")
        print(" [5] Remove Auto-Reconnect on Windows Boot")
        print(" [6] View Status & Recent Logs")
        print(" [0] Exit")
        print("==============================================================")

        choice = input("Enter choice [0-6]: ").strip()

        if choice == "1":
            print("\nFormat: your-name.ngrok-free.app or mysite.ngrok-free.website")
            new_domain = input(f"Enter your reserved permanent domain [{current_domain}]: ").strip()
            if new_domain:
                # Clean up domain
                new_domain = new_domain.replace("https://", "").replace("http://", "").strip().rstrip("/")
                cfg["permanent_domain"] = new_domain
                save_config(cfg)
        elif choice == "2":
            print("\nGet your authtoken at: https://dashboard.ngrok.com/get-started/your-authtoken")
            new_token = input("Paste your Ngrok Authtoken: ").strip()
            if new_token:
                cfg["authtoken"] = new_token
                save_config(cfg)
        elif choice == "3":
            print("\nStarting gateway supervisor...\n")
            try:
                subprocess.run([sys.executable, os.path.join(PROJECT_DIR, "gateway.py")])
            except KeyboardInterrupt:
                print("\nGateway stopped.")
        elif choice == "4":
            print("\nInstalling Auto-Reconnect on Windows Boot...")
            ps_script = os.path.join(PROJECT_DIR, "install_boot_startup.ps1")
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script])
            input("\nPress Enter to return to menu...")
        elif choice == "5":
            print("\nRemoving Auto-Reconnect from Windows Boot...")
            ps_script = os.path.join(PROJECT_DIR, "uninstall_boot_startup.ps1")
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script])
            input("\nPress Enter to return to menu...")
        elif choice == "6":
            show_status()
            input("Press Enter to return to menu...")
        elif choice == "0":
            break

if __name__ == "__main__":
    main()
