import sqlite3
import os

# Always resolve the DB path relative to this file's directory (backend/)
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vehicle_parking.db")

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # allows dict-style access to rows
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            address TEXT,
            role TEXT NOT NULL DEFAULT 'user'
        );
    ''')

    # Migrate existing databases: add missing columns if they don't exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "pin_code" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN pin_code TEXT")
    if "full_name" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    if "address" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN address TEXT")
    # PARKING LOTS table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_lots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            address TEXT,
            pincode TEXT,
            total_spots INTEGER
        );
    ''')

    # PARKING SPOTS table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_spot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            spot_number INTEGER NOT NULL,
            is_booked INTEGER DEFAULT 0,
            FOREIGN KEY (lot_id) REFERENCES parking_lots(id) ON DELETE CASCADE
        );
    ''')

    # RESERVATIONS table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            spot_id INTEGER,
            vehicle_no TEXT NOT NULL,
            checkin_time TEXT,
            checkout_time TEXT,
            status TEXT DEFAULT 'O',
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (spot_id) REFERENCES parking_spot(id)
        );
    ''')

    # CARS table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_number TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')



    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        """, ("admin1", "adminpass", "admin"))
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        """, ("user1", "userpass", "user"))



    conn.commit()
    conn.close()
