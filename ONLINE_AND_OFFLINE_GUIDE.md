# EvacuMate - Online & Offline Access Guide 🌐💻

Welcome to **EvacuMate (Relief & Shelter Helper)**! This guide explains how to run and access your application both **offline** (local computer and local network) and **online** (cloud hosting and web sharing).

---

## 1. 📴 Offline Access (No Internet Required)

### Mode A: Local Computer (Single User / Admin)
1. **Desktop Shortcut**: Double-click the **EvacuMate App** shortcut on your Desktop.
2. Alternatively, run `run.bat` inside the project folder.
3. The server will start automatically and open your default web browser at:
   - `http://127.0.0.1:8550` or `http://localhost:8550`

### Mode B: Local Wi-Fi / LAN Network (Multi-Device in Shelter/Office)
Multiple smartphones, tablets, or laptops in the same building/shelter can connect to EvacuMate without needing internet!
1. Start EvacuMate on the host computer.
2. Look at the Command Prompt window to find your **Network Access IP** (e.g., `http://192.168.1.15:8550`).
3. On any mobile phone, tablet, or laptop connected to the **same Wi-Fi router**:
   - Open Chrome, Safari, or Edge.
   - Enter `http://<YOUR_LOCAL_IP>:8550` (e.g. `http://192.168.1.15:8550`).

> 💡 **Tip**: Make sure Windows Firewall allows port `8550` if other devices have trouble connecting.

---

## 2. 🌐 Online Access (Public Internet Access)

### Option A: Free 24/7 Cloud Hosting on Render.com (Recommended)
You can deploy EvacuMate to the web for free so anyone can access it anywhere in the world:

1. **Push to GitHub**:
   - Upload your project repository to GitHub.
2. **Deploy on Render**:
   - Go to [render.com](https://render.com) and create a free account.
   - Click **New +** -> **Web Service**.
   - Connect your GitHub repository.
   - Render will automatically detect `render.yaml` or use:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn wsgi:app`
3. **Done!** Render will give you a public URL like `https://evacumate-relief-helper.onrender.com`.

### Option B: Quick Instant Web Tunneling (ngrok / Cloudflare Tunnel)
If you want to temporarily share your running local server to someone over the internet:
1. Download [ngrok](https://ngrok.com) or `cloudflared`.
2. Run command:
   ```cmd
   ngrok http 8550
   ```
3. Copy the generated `https://xxxx.ngrok-free.app` URL and send it to your team!

---

## 3. 📂 Database & Data Safety
- Your data is stored in `database/evacumate.db` (SQLite database).
- It is saved locally on your computer, keeping all relief center records intact even when offline.
- Backing up `database/evacumate.db` creates a complete backup of all evacuees, families, and inventory data.
