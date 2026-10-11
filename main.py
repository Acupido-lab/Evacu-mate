import os
import sys
import socket
from flask import Flask, render_template, jsonify, request

import database

def get_bundle_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

bundle_dir = get_bundle_dir()
app = Flask(
    __name__,
    static_folder=os.path.join(bundle_dir, 'static'),
    template_folder=os.path.join(bundle_dir, 'templates')
)

# Ensure database is initialized on startup
try:
    database.init_db()
except Exception as e:
    print("Database init info:", e)

# Resolve local IP address
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Resolve public gateway URL if configured
def get_public_gateway_url():
    # 1. Check live status file from supervisor
    status_path = os.path.join(bundle_dir, 'gateway_status.json')
    if os.path.exists(status_path):
        try:
            import json
            with open(status_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('status') == 'online' and data.get('public_url'):
                    return data.get('public_url')
        except Exception:
            pass

    # 2. Check gateway_config.json
    config_path = os.path.join(bundle_dir, 'gateway_config.json')
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                domain = cfg.get('permanent_domain', '').strip()
                if domain and 'YOUR_' not in domain.upper() and domain != 'evacumate-relief.ngrok-free.app':
                    domain = domain.replace('http://', '').replace('https://', '').strip('/')
                    return f"https://{domain}"
        except Exception:
            pass

    # 3. Check environment variables
    env_domain = os.environ.get('PERMANENT_DOMAIN') or os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('PUBLIC_URL')
    if env_domain:
        if not env_domain.startswith('http://') and not env_domain.startswith('https://'):
            return f"https://{env_domain}"
        return env_domain

    return None

# Initialize offline mDNS broadcaster & Port 80 redirector
try:
    import offline_broadcaster
    offline_broadcaster.init_offline_broadcaster(target_port=8550)
except Exception as e:
    print("Offline broadcaster init note:", e)

# Serve Frontend
@app.route('/')
def index():
    return render_template('index.html')

@app.after_request
def add_tunnel_and_cors_headers(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# ==========================================
# API ENDPOINTS
# ==========================================

@app.route('/api/server-info', methods=['GET'])
def server_info():
    port = int(os.environ.get('PORT', 8550))
    local_ip = get_local_ip()
    return jsonify({
        "ip": local_ip,
        "port": port,
        "offline_permanent_url": f"http://evacumate.local:{port}",
        "network_ip_url": f"http://{local_ip}:{port}",
        "public_url": get_public_gateway_url()
    })

@app.route('/api/qr-code', methods=['GET'])
def get_qr_code():
    port = int(os.environ.get('PORT', 8550))
    target = request.args.get('target', 'mdns')
    local_ip = get_local_ip()
    
    if target == 'ip':
        url = f"http://{local_ip}:{port}"
    elif target == 'public':
        url = get_public_gateway_url() or f"http://evacumate.local:{port}"
    else:
        url = f"http://evacumate.local:{port}"

    try:
        import qrcode
        import qrcode.image.svg
        import io
        from flask import Response
        factory = qrcode.image.svg.SvgImage
        img = qrcode.make(url, image_factory=factory)
        buf = io.BytesIO()
        img.save(buf)
        return Response(buf.getvalue(), mimetype='image/svg+xml')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    
    user = database.authenticate_user(username, password)
    if user:
        return jsonify({
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"]
        })
    else:
        return jsonify({"error": "Invalid username or password."}), 400

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'Staff')
    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    
    success = database.register_user(username, password, role)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Username already exists."}), 400

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    def delay_exit():
        import time
        time.sleep(0.5)
        os._exit(0)

    import threading
    threading.Thread(target=delay_exit).start()
    return jsonify({"success": True, "message": "Server is shutting down..."})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_families = database.get_families_count()
        total_evacuees = database.get_evacuees_count()
        total_capacity, total_occupied = database.get_rooms_stats()
        total_items = database.get_inventory_count()
        
        recent_evacuees_raw = database.get_recent_evacuees(5)
        recent_evacuees = [dict(row) for row in recent_evacuees_raw]
        
        recent_dists_raw = database.get_recent_distributions(5)
        recent_distributions = [dict(row) for row in recent_dists_raw]
        
        return jsonify({
            "total_families": total_families,
            "total_evacuees": total_evacuees,
            "total_occupied": total_occupied,
            "total_capacity": total_capacity,
            "total_items": total_items,
            "recent_evacuees": recent_evacuees,
            "recent_distributions": recent_distributions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Families CRUD
@app.route('/api/families', methods=['GET'])
def get_families():
    search = request.args.get('search', '')
    families_raw = database.get_families(search)
    families = [dict(row) for row in families_raw]
    return jsonify(families)

@app.route('/api/families', methods=['POST'])
def add_family():
    data = request.json or {}
    family_name = data.get('family_name', '').strip()
    contact_number = data.get('contact_number', '').strip()
    address = data.get('address', '').strip()
    
    if not family_name:
        return jsonify({"error": "Family Surname is required."}), 400
        
    try:
        database.add_family(family_name, contact_number, address)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/families/<int:family_id>', methods=['PUT'])
def update_family(family_id):
    data = request.json or {}
    family_name = data.get('family_name', '').strip()
    contact_number = data.get('contact_number', '').strip()
    address = data.get('address', '').strip()
    
    if not family_name:
        return jsonify({"error": "Family Surname is required."}), 400
        
    try:
        database.update_family(family_id, family_name, contact_number, address)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/families/<int:family_id>', methods=['DELETE'])
def delete_family(family_id):
    try:
        database.delete_family(family_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Evacuees CRUD
@app.route('/api/evacuees', methods=['GET'])
def get_evacuees():
    search = request.args.get('search', '')
    evacuees_raw = database.get_evacuees(search)
    evacuees = [dict(row) for row in evacuees_raw]
    return jsonify(evacuees)

@app.route('/api/evacuees', methods=['POST'])
def add_evacuee():
    data = request.json or {}
    fullname = data.get('fullname', '').strip()
    raw_age = data.get('age')
    age = int(raw_age) if raw_age not in (None, '') else None
    gender = data.get('gender', 'Other')
    medical_condition = data.get('medical_condition', '').strip()
    family_id = int(data['family_id']) if data.get('family_id') is not None else None
    raw_room_id = data.get('room_id')
    room_id = int(raw_room_id) if raw_room_id not in (None, '', 'null') else None
    
    if not fullname or family_id is None:
        return jsonify({"error": "Full Name and Family Association are required."}), 400
        
    try:
        database.add_evacuee(family_id, fullname, age, gender, medical_condition, room_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/evacuees/<int:evacuee_id>', methods=['PUT'])
def update_evacuee(evacuee_id):
    data = request.json or {}
    fullname = data.get('fullname', '').strip()
    raw_age = data.get('age')
    age = int(raw_age) if raw_age not in (None, '') else None
    gender = data.get('gender', 'Other')
    medical_condition = data.get('medical_condition', '').strip()
    family_id = int(data['family_id']) if data.get('family_id') is not None else None
    raw_room_id = data.get('room_id')
    room_id = int(raw_room_id) if raw_room_id not in (None, '', 'null') else None
    
    if not fullname or family_id is None:
        return jsonify({"error": "Full Name and Family Association are required."}), 400
        
    try:
        database.update_evacuee(evacuee_id, family_id, fullname, age, gender, medical_condition, room_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/evacuees/<int:evacuee_id>', methods=['DELETE'])
def delete_evacuee(evacuee_id):
    try:
        database.delete_evacuee(evacuee_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Rooms CRUD
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    search = request.args.get('search', '')
    rooms_raw = database.get_rooms(search)
    rooms = [dict(row) for row in rooms_raw]
    return jsonify(rooms)

@app.route('/api/rooms', methods=['POST'])
def add_room():
    data = request.json or {}
    room_name = data.get('room_name', '').strip()
    capacity = data.get('capacity')
    
    if not room_name or capacity is None:
        return jsonify({"error": "Valid name and positive capacity are required."}), 400
        
    try:
        cap = int(capacity)
        if cap <= 0:
            return jsonify({"error": "Room capacity must be greater than 0."}), 400
        database.add_room(room_name, cap)
        return jsonify({"success": True})
    except (ValueError, TypeError):
        return jsonify({"error": "Capacity must be a valid integer."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
def update_room(room_id):
    data = request.json or {}
    room_name = data.get('room_name', '').strip()
    capacity = data.get('capacity')
    
    if not room_name or capacity is None:
        return jsonify({"error": "Valid room name and capacity are required."}), 400
        
    try:
        cap = int(capacity)
        if cap <= 0:
            return jsonify({"error": "Room capacity must be greater than 0."}), 400
        database.update_room(room_id, room_name, cap)
        return jsonify({"success": True})
    except (ValueError, TypeError):
        return jsonify({"error": "Capacity must be a valid integer."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    try:
        database.delete_room(room_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Inventory CRUD
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    search = request.args.get('search', '')
    inventory_raw = database.get_inventory(search)
    inventory = [dict(row) for row in inventory_raw]
    return jsonify(inventory)

@app.route('/api/inventory', methods=['POST'])
def add_inventory():
    data = request.json or {}
    item_name = data.get('item_name', '').strip()
    quantity = data.get('quantity')
    unit = data.get('unit', '').strip()
    
    if not item_name or quantity is None or not unit:
        return jsonify({"error": "All fields with valid values are required."}), 400
        
    try:
        qty = int(quantity)
        if qty < 0:
            return jsonify({"error": "Quantity cannot be negative."}), 400
        database.add_inventory(item_name, qty, unit)
        return jsonify({"success": True})
    except (ValueError, TypeError):
        return jsonify({"error": "Quantity must be a valid integer."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
def update_inventory(item_id):
    data = request.json or {}
    item_name = data.get('item_name', '').strip()
    quantity = data.get('quantity')
    unit = data.get('unit', '').strip()
    
    if not item_name or quantity is None or not unit:
        return jsonify({"error": "All fields with valid values are required."}), 400
        
    try:
        qty = int(quantity)
        if qty < 0:
            return jsonify({"error": "Quantity cannot be negative."}), 400
        database.update_inventory(item_id, item_name, qty, unit)
        return jsonify({"success": True})
    except (ValueError, TypeError):
        return jsonify({"error": "Quantity must be a valid integer."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
def delete_inventory(item_id):
    try:
        database.delete_inventory(item_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Distributions CRUD
@app.route('/api/distributions', methods=['GET'])
def get_distributions():
    search = request.args.get('search', '')
    distributions_raw = database.get_distributions(search)
    distributions = [dict(row) for row in distributions_raw]
    return jsonify(distributions)

@app.route('/api/distributions', methods=['POST'])
def add_distribution():
    data = request.json or {}
    family_id = data.get('family_id')
    item_id = data.get('item_id')
    quantity = data.get('quantity')
    distribution_date = data.get('distribution_date')
    
    if family_id is None or item_id is None or quantity is None or not distribution_date:
        return jsonify({"error": "All fields are required."}), 400
        
    try:
        qty = int(quantity)
        if qty <= 0:
            return jsonify({"error": "Quantity to issue must be greater than 0."}), 400
        success = database.add_distribution(int(family_id), int(item_id), qty, distribution_date)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Insufficient stock to issue requested quantity!"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Quantity must be a valid integer."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/distributions/revert/<int:distribution_id>', methods=['POST'])
def revert_distribution(distribution_id):
    try:
        success = database.revert_distribution(distribution_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to revert distribution record."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Users CRUD
@app.route('/api/users', methods=['GET'])
def get_users():
    search = request.args.get('search', '')
    users_raw = database.get_users(search)
    users = [dict(row) for row in users_raw]
    return jsonify(users)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        database.delete_user(user_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def ensure_gateway_tunnel_active():
    """Starts the permanent ngrok tunnel in the background if configured and not already running."""
    config_path = os.path.join(bundle_dir, 'gateway_config.json')
    if not os.path.exists(config_path):
        return
    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        domain = cfg.get('permanent_domain', '').strip()
        token = cfg.get('authtoken', '').strip()
        if not domain or 'YOUR_' in domain.upper() or not token:
            return

        ngrok_bin = os.path.join(bundle_dir, 'bin', 'ngrok.exe')
        if not os.path.isfile(ngrok_bin):
            return

        # Check if ngrok is already running
        import subprocess
        res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ngrok.exe"], capture_output=True, text=True)
        if "ngrok.exe" in res.stdout:
            return  # ngrok is already active

        cmd = [
            ngrok_bin,
            "http",
            f"--url=https://{domain}",
            "--host-header=rewrite",
            "127.0.0.1:8550"
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8550))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Ensure permanent public gateway tunnel is active
    ensure_gateway_tunnel_active()

    local_ip = get_local_ip()
    pub_url = get_public_gateway_url()

    print("=" * 66)
    print("    EvacuMate Relief & Shelter Helper (Permanent Public Online)    ")
    print("=" * 66)
    if pub_url:
        print(f"  PERMANENT PUBLIC ONLINE URL (Any Device) : {pub_url}")
    print(f"  Offline Local Link (All Devices)         : http://evacumate.local:{port}")
    print(f"  Direct Wi-Fi / Hotspot Fallback          : http://{local_ip}:{port}")
    print(f"  Local Host Computer                      : http://127.0.0.1:{port}")
    print("=" * 66)
    
    # Auto-open browser window on startup directly to permanent public link!
    if os.environ.get('PORT') is None and os.environ.get('NO_BROWSER') is None:
        import webbrowser
        import threading
        import time
        def open_browser():
            time.sleep(1.5)
            target_url = pub_url if pub_url else f"http://127.0.0.1:{port}"
            try:
                webbrowser.open(target_url)
            except Exception:
                pass

        threading.Thread(target=open_browser, daemon=True).start()

    # Run the web server (Prefer multithreaded Waitress for seamless public gateway handling)
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port, threads=8)
    except Exception:
        app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
