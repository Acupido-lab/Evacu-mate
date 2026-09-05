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

# Serve Frontend
@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# API ENDPOINTS
# ==========================================

@app.route('/api/server-info', methods=['GET'])
def server_info():
    return jsonify({"ip": get_local_ip()})

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
        import signal
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)

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
    age = data.get('age')
    gender = data.get('gender', 'Other')
    medical_condition = data.get('medical_condition', '').strip()
    family_id = data.get('family_id')
    room_id = data.get('room_id')
    
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
    age = data.get('age')
    gender = data.get('gender', 'Other')
    medical_condition = data.get('medical_condition', '').strip()
    family_id = data.get('family_id')
    room_id = data.get('room_id')
    
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8550))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    
    local_ip = get_local_ip()
    print(f"Starting EvacuMate Relief & Shelter Helper...")
    print(f"Local Access: http://127.0.0.1:{port}")
    print(f"Network Access: http://{local_ip}:{port}")
    
    # Auto-open browser window on startup (for local / EXE execution)
    if os.environ.get('PORT') is None and os.environ.get('NO_BROWSER') is None:
        import webbrowser
        import threading
        import time
        def open_browser():
            time.sleep(1.2)
            try:
                webbrowser.open(f"http://127.0.0.1:{port}")
            except Exception:
                pass

        threading.Thread(target=open_browser, daemon=True).start()

    # Run the web server
    app.run(host='0.0.0.0', port=port, debug=debug)
