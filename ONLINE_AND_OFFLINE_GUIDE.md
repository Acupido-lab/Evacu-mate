# EvacuMate - Online & Offline Access Guide 🌐💻

Welcome to **EvacuMate (Relief & Shelter Helper)**! This guide explains how to run and access your application both **offline** (local computer and local network) and **online** (cloud hosting and web sharing).

---

## 1. 📴 Offline Access (No Internet Required)

### 🌟 Permanent Offline Link (Never Changes on Any Device)
No more asking "what is the IP address today?". EvacuMate broadcasts its own permanent local domain across your Wi-Fi or phone hotspot:
- **Permanent URL**: `http://evacumate.local:8550` (or simply `http://evacumate.local`)
- **Device Compatibility**:
  - **iPhones & iPads**: Works natively in Safari and Chrome.
  - **Android Devices (12+)**: Works natively in Google Chrome.
  - **Windows & Mac**: Works in Chrome, Edge, and Safari.
  - **Host Computer**: `http://evacumate.local:8550` or `http://127.0.0.1:8550`.

### 📱 Instant Mobile Camera QR Code
1. Start EvacuMate on your laptop.
2. In the top-right header, click **📱 Connect Mobile**.
3. A large QR code appears on screen.
4. Point any phone or tablet camera at the screen to open EvacuMate immediately in Chrome—zero typing needed!

### 📲 Install as a Mobile App (PWA)
Once opened in Chrome on Android or Safari on iOS:
1. Tap the browser menu (⋮ or Share icon).
2. Tap **"Add to Home Screen"** or **"Install App"**.
3. EvacuMate now appears with an app icon on your home screen and operates with full offline caching!

### Direct Wi-Fi IP (Fallback for Older Androids)
If you have an older smartphone (Android 11 or older) that lacks mDNS support:
1. Look at the terminal window or the "Connect Mobile" modal to find your Wi-Fi IP (e.g. `http://192.168.18.192:8550`).
2. Type that into Chrome or scan the "Direct IP" QR code toggle.

---

## 2. 🌐 Permanent Public Online Runtime Gateway (Fixed Public URL)

To give EvacuMate a single fixed public URL that **never changes, never expires, and auto-reconnects on boot**:

### The 6 Golden Gateway Rules
1. **Bind to ONE Permanent Reserved Domain Only**: No random subdomains.
2. **Identical URL Across Restarts/Reboots**: Always binds to your reserved static domain.
3. **No Temporary Links**: Zero random URLs that break client bookmarks or gadgets.
4. **Auto-Reconnect on Windows Boot**: Background service automatically starts on PC startup.
5. **Full Global Internet Accessibility**: Reachable worldwide from any phone, tablet, or laptop.
6. **HTTPS Enabled by Default**: Secured with TLS certificates out of the box.

---

### Setup Instructions (3 Easy Minutes)

#### Step 1: Claim your 100% Free Lifetime Static Domain
1. Log in or create a free account at [dashboard.ngrok.com](https://dashboard.ngrok.com).
2. Go to **Cloud Edge** -> **Domains** (or [dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains)).
3. Click **+ New Domain** to claim your free static domain (e.g. `mysite.ngrok-free.website` or `yourname.ngrok-free.app`).
4. Go to **Get Started** -> **Your Authtoken** (or [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)) and copy your authtoken.

#### Step 2: Configure the Gateway
- Open `gateway_config.json` in the project folder (or run `configure_gateway.bat`):
  ```json
  {
    "permanent_domain": "your-reserved-domain.ngrok-free.app",
    "authtoken": "YOUR_NGROK_AUTHTOKEN_HERE",
    "port": 8550,
    "auto_reconnect": true
  }
  ```

#### Step 3: Enable Auto-Reconnect on Windows Boot
- Run `configure_gateway.bat` and press **[4]** (or right-click `install_boot_startup.ps1` and select *Run with PowerShell*).
- This registers the gateway to run silently in the background whenever Windows boots or logs in!

#### Step 4: Run or Test
- **Interactive Mode**: Double-click `run_gateway.bat` or `EvacuMate Permanent Gateway` on your Desktop.
- **Silent Background Mode**: Run `wscript run_gateway_silent.vbs`.

---

### Option B: 24/7 Cloud Hosting on Render.com (Serverless Cloud)
If you need 24/7 online availability even when your host PC is turned completely off:
1. Push your repository to GitHub (`https://github.com/Acupido-lab/Evacu-mate.git`).
2. Log in to [render.com](https://render.com) and create a **Web Service** connected to your repo.
3. Render automatically picks up `render.yaml` and gives you a 24/7 public URL like `https://evacumate-relief-helper.onrender.com`.

---

## 3. 📂 Database & Data Safety
- Your data is stored in `database/evacumate.db` (SQLite database).
- It is saved locally on your computer, keeping all relief center records intact even when offline.
- Backing up `database/evacumate.db` creates a complete backup of all evacuees, families, and inventory data.
