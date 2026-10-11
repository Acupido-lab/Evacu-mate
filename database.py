import sqlite3
import os
import hashlib
import sys

def get_base_dir():
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
DATABASE = os.path.join(BASE_DIR, "database", "evacuation.db")
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

def get_db_connection():
    if hasattr(sys, '_MEIPASS'):
        exe_dir = os.path.dirname(sys.executable)
        target_dir = os.path.join(exe_dir, "database")
        os.makedirs(target_dir, exist_ok=True)
        target_db = os.path.join(target_dir, "evacuation.db")
        if not os.path.exists(target_db):
            bundled_db = os.path.join(sys._MEIPASS, "database", "evacuation.db")
            if os.path.exists(bundled_db):
                import shutil
                try:
                    shutil.copy2(bundled_db, target_db)
                except Exception:
                    pass
        conn = sqlite3.connect(target_db)
    else:
        conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # FAMILIES TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS families(
        family_id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_name TEXT NOT NULL,
        contact_number TEXT,
        address TEXT
    )
    """)

    # EVACUEES TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evacuees(
        evacuee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        fullname TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        medical_condition TEXT,
        room_id INTEGER,
        FOREIGN KEY(family_id) REFERENCES families(family_id)
    )
    """)

    # ROOMS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms(
        room_id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT,
        capacity INTEGER,
        occupied INTEGER DEFAULT 0
    )
    """)

    # INVENTORY TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory(
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        quantity INTEGER,
        unit TEXT
    )
    """)

    # DISTRIBUTION TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS distribution(
        distribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        item_id INTEGER,
        quantity INTEGER,
        distribution_date TEXT
    )
    """)

    conn.commit()

    cursor.execute("""
        UPDATE rooms SET occupied = (
            SELECT COUNT(*) FROM evacuees WHERE evacuees.room_id = rooms.room_id
        )
    """)
    conn.commit()

    # Seed default admin user if none exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_pass = hash_password("admin123")
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", admin_pass, "Admin")
        )
        conn.commit()
        print("Default admin user seeded: admin / admin123")

    conn.close()
    print("Database Created and Initialized Successfully!")


# ==========================================
# CRUD HELPERS FOR USERS
# ==========================================

def authenticate_user(username, password):
    conn = get_db_connection()
    hashed = hash_password(password)
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, hashed)
    ).fetchone()
    conn.close()
    return user

def register_user(username, password, role):
    conn = get_db_connection()
    hashed = hash_password(password)
    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def get_users_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

def get_users(search=""):
    conn = get_db_connection()
    if search:
        users = conn.execute(
            "SELECT user_id, username, role FROM users WHERE username LIKE ? ORDER BY username ASC",
            (f"%{search}%",)
        ).fetchall()
    else:
        users = conn.execute("SELECT user_id, username, role FROM users ORDER BY username ASC").fetchall()
    conn.close()
    return users

def delete_user(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ==========================================
# CRUD HELPERS FOR FAMILIES
# ==========================================

def get_families_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM families").fetchone()[0]
    conn.close()
    return count

def get_families(search=""):
    conn = get_db_connection()
    if search:
        families = conn.execute("""
            SELECT * FROM families 
            WHERE family_name LIKE ? OR contact_number LIKE ? OR address LIKE ? 
            ORDER BY family_id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        families = conn.execute("SELECT * FROM families ORDER BY family_id DESC").fetchall()
    conn.close()
    return families

def add_family(name, contact, address):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO families (family_name, contact_number, address) VALUES (?, ?, ?)",
        (name, contact, address)
    )
    conn.commit()
    conn.close()

def update_family(family_id, name, contact, address):
    conn = get_db_connection()
    conn.execute("""
        UPDATE families 
        SET family_name = ?, contact_number = ?, address = ? 
        WHERE family_id = ?
    """, (name, contact, address, family_id))
    conn.commit()
    conn.close()

def delete_family(family_id):
    conn = get_db_connection()
    # Decrement occupied count in rooms for any evacuees being deleted
    evacuees = conn.execute("SELECT room_id FROM evacuees WHERE family_id = ?", (family_id,)).fetchall()
    room_ids_to_update = set(ev["room_id"] for ev in evacuees if ev["room_id"])
    
    # Delete connected records
    conn.execute("DELETE FROM evacuees WHERE family_id = ?", (family_id,))
    conn.execute("DELETE FROM distribution WHERE family_id = ?", (family_id,))
    conn.execute("DELETE FROM families WHERE family_id = ?", (family_id,))
    
    for rid in room_ids_to_update:
        conn.execute("UPDATE rooms SET occupied = (SELECT COUNT(*) FROM evacuees WHERE room_id = ?) WHERE room_id = ?", (rid, rid))
        
    conn.commit()
    conn.close()


# ==========================================
# CRUD HELPERS FOR EVACUEES
# ==========================================

def get_evacuees_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM evacuees").fetchone()[0]
    conn.close()
    return count

def get_evacuees(search=""):
    conn = get_db_connection()
    if search:
        evacuees = conn.execute("""
            SELECT e.*, f.family_name, r.room_name 
            FROM evacuees e
            LEFT JOIN families f ON e.family_id = f.family_id
            LEFT JOIN rooms r ON e.room_id = r.room_id
            WHERE e.fullname LIKE ? OR f.family_name LIKE ? OR r.room_name LIKE ? OR e.medical_condition LIKE ?
            ORDER BY e.evacuee_id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        evacuees = conn.execute("""
            SELECT e.*, f.family_name, r.room_name 
            FROM evacuees e
            LEFT JOIN families f ON e.family_id = f.family_id
            LEFT JOIN rooms r ON e.room_id = r.room_id
            ORDER BY e.evacuee_id DESC
        """).fetchall()
    conn.close()
    return evacuees

def add_evacuee(family_id, fullname, age, gender, medical_condition, room_id):
    conn = get_db_connection()
    if room_id:
        room = conn.execute("""
            SELECT capacity, (SELECT COUNT(*) FROM evacuees WHERE room_id = ?) AS occupied 
            FROM rooms WHERE room_id = ?
        """, (room_id, room_id)).fetchone()
        if room and room["occupied"] >= room["capacity"]:
            conn.close()
            raise Exception("Selected room is already at full capacity!")

    conn.execute("""
        INSERT INTO evacuees (family_id, fullname, age, gender, medical_condition, room_id) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (family_id, fullname, age, gender, medical_condition, room_id))
    if room_id:
        conn.execute("UPDATE rooms SET occupied = (SELECT COUNT(*) FROM evacuees WHERE room_id = ?) WHERE room_id = ?", (room_id, room_id))
    conn.commit()
    conn.close()

def update_evacuee(evacuee_id, family_id, fullname, age, gender, medical_condition, room_id):
    conn = get_db_connection()
    current = conn.execute("SELECT room_id FROM evacuees WHERE evacuee_id = ?", (evacuee_id,)).fetchone()
    old_room_id = current["room_id"] if current else None

    if room_id and str(room_id) != str(old_room_id):
        room = conn.execute("""
            SELECT capacity, (SELECT COUNT(*) FROM evacuees WHERE room_id = ?) AS occupied 
            FROM rooms WHERE room_id = ?
        """, (room_id, room_id)).fetchone()
        if room and room["occupied"] >= room["capacity"]:
            conn.close()
            raise Exception("Selected room is already at full capacity!")

    conn.execute("""
        UPDATE evacuees 
        SET family_id = ?, fullname = ?, age = ?, gender = ?, medical_condition = ?, room_id = ?
        WHERE evacuee_id = ?
    """, (family_id, fullname, age, gender, medical_condition, room_id, evacuee_id))

    if old_room_id:
        conn.execute("UPDATE rooms SET occupied = (SELECT COUNT(*) FROM evacuees WHERE room_id = ?) WHERE room_id = ?", (old_room_id, old_room_id))
    if room_id:
        conn.execute("UPDATE rooms SET occupied = (SELECT COUNT(*) FROM evacuees WHERE room_id = ?) WHERE room_id = ?", (room_id, room_id))
    
    conn.commit()
    conn.close()

def delete_evacuee(evacuee_id):
    conn = get_db_connection()
    current = conn.execute("SELECT room_id FROM evacuees WHERE evacuee_id = ?", (evacuee_id,)).fetchone()
    conn.execute("DELETE FROM evacuees WHERE evacuee_id = ?", (evacuee_id,))
    if current and current["room_id"]:
        room_id = current["room_id"]
        conn.execute("UPDATE rooms SET occupied = (SELECT COUNT(*) FROM evacuees WHERE room_id = ?) WHERE room_id = ?", (room_id, room_id))
    conn.commit()
    conn.close()


# ==========================================
# CRUD HELPERS FOR ROOMS
# ==========================================

def get_rooms_stats():
    conn = get_db_connection()
    cap_row = conn.execute("SELECT SUM(capacity) FROM rooms").fetchone()
    occ_row = conn.execute("SELECT COUNT(*) FROM evacuees WHERE room_id IS NOT NULL").fetchone()
    conn.close()
    total_capacity = cap_row[0] if cap_row and cap_row[0] is not None else 0
    total_occupied = occ_row[0] if occ_row and occ_row[0] is not None else 0
    return total_capacity, total_occupied

def get_rooms(search=""):
    conn = get_db_connection()
    if search:
        rooms = conn.execute("""
            SELECT r.room_id, r.room_name, r.capacity,
                   (SELECT COUNT(*) FROM evacuees e WHERE e.room_id = r.room_id) AS occupied
            FROM rooms r
            WHERE r.room_name LIKE ?
            ORDER BY r.room_name ASC
        """, (f"%{search}%",)).fetchall()
    else:
        rooms = conn.execute("""
            SELECT r.room_id, r.room_name, r.capacity,
                   (SELECT COUNT(*) FROM evacuees e WHERE e.room_id = r.room_id) AS occupied
            FROM rooms r
            ORDER BY r.room_name ASC
        """).fetchall()
    conn.close()
    return rooms

def add_room(name, capacity):
    conn = get_db_connection()
    conn.execute("INSERT INTO rooms (room_name, capacity, occupied) VALUES (?, ?, 0)", (name, capacity))
    conn.commit()
    conn.close()

def update_room(room_id, name, capacity):
    conn = get_db_connection()
    conn.execute("UPDATE rooms SET room_name = ?, capacity = ? WHERE room_id = ?", (name, capacity, room_id))
    conn.commit()
    conn.close()

def delete_room(room_id):
    conn = get_db_connection()
    conn.execute("UPDATE evacuees SET room_id = NULL WHERE room_id = ?", (room_id,))
    conn.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()

# ==========================================
# CRUD HELPERS FOR INVENTORY
# ==========================================

def get_inventory_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    conn.close()
    return count

def get_inventory(search=""):
    conn = get_db_connection()
    if search:
        items = conn.execute("SELECT * FROM inventory WHERE item_name LIKE ? ORDER BY item_name ASC", (f"%{search}%",)).fetchall()
    else:
        items = conn.execute("SELECT * FROM inventory ORDER BY item_name ASC").fetchall()
    conn.close()
    return items

def add_inventory(name, quantity, unit):
    conn = get_db_connection()
    conn.execute("INSERT INTO inventory (item_name, quantity, unit) VALUES (?, ?, ?)", (name, quantity, unit))
    conn.commit()
    conn.close()

def update_inventory(item_id, name, quantity, unit):
    conn = get_db_connection()
    conn.execute("UPDATE inventory SET item_name = ?, quantity = ?, unit = ? WHERE item_id = ?", (name, quantity, unit, item_id))
    conn.commit()
    conn.close()

def delete_inventory(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM inventory WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM distribution WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()


# ==========================================
# CRUD HELPERS FOR DISTRIBUTIONS
# ==========================================

def get_recent_evacuees(limit=5):
    conn = get_db_connection()
    evacuees = conn.execute(f"""
        SELECT e.fullname, e.age, e.gender, r.room_name 
        FROM evacuees e 
        LEFT JOIN rooms r ON e.room_id = r.room_id 
        ORDER BY e.evacuee_id DESC LIMIT {int(limit)}
    """).fetchall()
    conn.close()
    return evacuees

def get_recent_distributions(limit=5):
    conn = get_db_connection()
    dists = conn.execute(f"""
        SELECT f.family_name, i.item_name, d.quantity, i.unit, d.distribution_date 
        FROM distribution d
        JOIN families f ON d.family_id = f.family_id
        JOIN inventory i ON d.item_id = i.item_id
        ORDER BY d.distribution_id DESC LIMIT {int(limit)}
    """).fetchall()
    conn.close()
    return dists

def get_distributions(search=""):
    conn = get_db_connection()
    if search:
        dists = conn.execute("""
            SELECT d.*, f.family_name, i.item_name, i.unit 
            FROM distribution d
            JOIN families f ON d.family_id = f.family_id
            JOIN inventory i ON d.item_id = i.item_id
            WHERE f.family_name LIKE ? OR i.item_name LIKE ? OR d.distribution_date LIKE ?
            ORDER BY d.distribution_id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        dists = conn.execute("""
            SELECT d.*, f.family_name, i.item_name, i.unit 
            FROM distribution d
            JOIN families f ON d.family_id = f.family_id
            JOIN inventory i ON d.item_id = i.item_id
            ORDER BY d.distribution_id DESC
        """).fetchall()
    conn.close()
    return dists

def add_distribution(family_id, item_id, quantity, date):
    conn = get_db_connection()
    # Check if family exists
    fam = conn.execute("SELECT family_id FROM families WHERE family_id = ?", (family_id,)).fetchone()
    if not fam:
        conn.close()
        return False

    # Check if stock is sufficient
    item = conn.execute("SELECT quantity FROM inventory WHERE item_id = ?", (item_id,)).fetchone()
    if not item or item["quantity"] < int(quantity):
        conn.close()
        return False
    
    conn.execute("""
        INSERT INTO distribution (family_id, item_id, quantity, distribution_date) 
        VALUES (?, ?, ?, ?)
    """, (family_id, item_id, quantity, date))
    conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_id = ?", (quantity, item_id))
    conn.commit()
    conn.close()
    return True

def revert_distribution(distribution_id):
    conn = get_db_connection()
    dist = conn.execute("SELECT * FROM distribution WHERE distribution_id = ?", (distribution_id,)).fetchone()
    if dist:
        conn.execute("UPDATE inventory SET quantity = quantity + ? WHERE item_id = ?", (dist["quantity"], dist["item_id"]))
        conn.execute("DELETE FROM distribution WHERE distribution_id = ?", (distribution_id,))
        conn.commit()
        success = True
    else:
        success = False
    conn.close()
    return success

if __name__ == "__main__":
    init_db()
