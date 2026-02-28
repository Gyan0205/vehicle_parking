from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, url_for, flash, session
from flask_cors import CORS
from backend.models.db import initialize_database, get_db_connection
from datetime import datetime
import traceback
import sqlite3



app = Flask(__name__)
app.secret_key = 'supersecretkey123'
CORS(app)



# Initialize the SQLite database
initialize_database()



@app.route("/", methods=['GET', 'POST'])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            role = user["role"]
            if role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    message = None
    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        password = request.form["password"]
        address = request.form["address"]
        pin_code = request.form["pin_code"]
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (full_name, username, password, address, pin_code) VALUES (?, ?, ?, ?, ?)", (full_name, username, password, address, pin_code))
            conn.commit()
            message = "Registration successful! You can now log in."
        except sqlite3.IntegrityError:
            error = "Username already exists."
        finally:
            conn.close()
    return render_template("register.html", error=error, message=message)



@app.route('/admin/dashboard')
def admin_dashboard():
    conn = get_db_connection()
    lots = conn.execute("SELECT * FROM parking_lots").fetchall()
    parking_lots = []
    for lot in lots:
        lot_id = lot["id"]
        spots = conn.execute("SELECT spot_number, is_booked FROM parking_spot WHERE lot_id = ?", (lot_id,)).fetchall()
        occupied_count = sum(1 for spot in spots if spot["is_booked"])
        total_count = len(spots)
        parking_lots.append({
            "id": lot_id,
            "name": lot["name"],
            "occupied": occupied_count,
            "total": total_count,
            "parking_spot": spots
        })
    conn.close()
    return render_template("admin_dashboard.html", parking_lots=parking_lots)

@app.route('/admin/add_lot', methods=['POST'])
def add_lot():
    name = request.form['name']
    price = request.form['price']
    address = request.form['address']
    pincode = request.form['pincode']
    total_spots = int(request.form['total_spots'])
    conn = get_db_connection()
    cur = conn.cursor()
    # Step 1: Insert into parking_lot table
    cur.execute("""
        INSERT INTO parking_lots (name, price, address, pincode, total_spots)
        VALUES (?, ?, ?, ?, ?)
    """, (name, price, address, pincode, total_spots))
    lot_id = cur.lastrowid  # get the ID of the inserted parking lot
    # Step 2: Generate parking_spot entries
    for i in range(1, total_spots + 1):
        cur.execute("""
            INSERT INTO parking_spot (lot_id, spot_number, is_booked)
            VALUES (?, ?, 0)
        """, (lot_id, i))
    conn.commit()
    conn.close()
    flash("Parking Lot and spots added successfully!", "success")
    return redirect('/admin/dashboard')



@app.route("/admin/edit_lot/<int:lot_id>", methods=["GET", "POST"])
def edit_lot(lot_id):
    conn = get_db_connection()
    lot = conn.execute("SELECT * FROM parking_lots WHERE id = ?", (lot_id,)).fetchone()
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        address = request.form["address"]
        pincode = request.form["pincode"]
        total_spots = request.form["total_spots"]
        conn.execute("""
            UPDATE parking_lots 
            SET name = ?, price = ?, address = ?, pincode = ?, total_spots = ?
            WHERE id = ?
        """, (name, price, address, pincode, total_spots, lot_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))
    conn.close()
    return render_template("edit_lot.html", lot=lot)



@app.route("/admin/delete_lot/<int:lot_id>", methods=["GET"])
def delete_lot(lot_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM parking_lots WHERE id = ?", (lot_id,))
    conn.execute("DELETE FROM parking_spot WHERE lot_id = ?", (lot_id,))  # Remove its spots too
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))



# Removed broken /admin/parking-lots route (used wrong column names and was unused)



@app.route("/admin/users")
def users():
    conn = get_db_connection()
    users = conn.execute("SELECT id, full_name, username, address FROM users WHERE role = 'user'").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)



@app.route("/admin/search", methods=["GET"])
def search_lots():
    search_by = request.args.get("search_by")
    search_value = request.args.get("search_value")
    parking_lots = []
    user_info = None
    if search_by and search_value:
        conn = get_db_connection()
        cursor = conn.cursor()

        if search_by == "user_id":
            cursor.execute("SELECT * FROM users WHERE username = ?", (search_value,))
            user = cursor.fetchone()
            if user:
                user_info = dict(user)
            conn.close()
            return render_template("search_lots.html", parking_lots=[], user_info=user_info)
        elif search_by == "pin_code":
            cursor.execute("SELECT * FROM parking_lots WHERE pincode = ?", (search_value,))
            lots = cursor.fetchall()
            for lot in lots:
                cursor.execute("SELECT * FROM parking_spot WHERE lot_id = ?", (lot['id'],))
                spots = cursor.fetchall()
                lot_dict = dict(lot)
                lot_dict['parking_spot'] = spots
                lot_dict['occupied'] = sum(1 for s in spots if s['is_booked'])
                lot_dict['total'] = len(spots)
                parking_lots.append(lot_dict)
            conn.close()
    return render_template("search_lots.html", parking_lots=parking_lots, user_info=user_info)



@app.route('/user/dashboard', methods=['GET'])
def user_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    conn = get_db_connection()
    # Fetch recent reservations along with address from parking_lots
    recent_parking = conn.execute('''
        SELECT r.id, r.spot_id, r.vehicle_no, r.checkin_time, r.checkout_time,
               l.address AS location
        FROM reservations r
        JOIN parking_spot s ON r.spot_id = s.id
        JOIN parking_lots l ON s.lot_id = l.id
        WHERE r.user_id = ?
        ORDER BY r.checkin_time DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return render_template(
        'user_dashboard.html',
        recent_parking=recent_parking,
        search_results=[]
    )



@app.route('/user/search', methods=['GET'])
def search_parking_by_pincode():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for('login'))
    pincode = request.args.get('query', '').strip()
    conn = get_db_connection()
    lots = []
    if pincode:
        lots = conn.execute("""
            SELECT pl.id, pl.name, pl.address, pl.price,
                   COUNT(ps.id) - SUM(ps.is_booked) AS available
            FROM parking_lots pl
            JOIN parking_spot ps ON pl.id = ps.lot_id
            WHERE pl.pincode = ?
            GROUP BY pl.id
        """, (pincode,)).fetchall()
    reservations = conn.execute("""
        SELECT r.id, r.spot_id, pl.address AS location, r.vehicle_no, r.checkin_time, r.checkout_time
        FROM reservations r
        JOIN parking_spot ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.user_id = ?
        ORDER BY r.checkin_time DESC
    """, (user_id,)).fetchall()
    conn.close()
    return render_template('user_dashboard.html', recent_parking=reservations, search_results=lots)



@app.route('/user/book/<int:lot_id>', methods=['POST'])
def book_parking(lot_id):
    try:
        user_id = session.get('user_id')
        vehicle_no = request.form.get('vehicle_no')
        if not vehicle_no:
            flash("Vehicle number is required.", "danger")
            return redirect(url_for('user_dashboard'))
        conn = get_db_connection()
        # Find an available spot
        spot = conn.execute(
            "SELECT id FROM parking_spot WHERE lot_id = ? AND is_booked = 0 LIMIT 1", 
            (lot_id,)
        ).fetchone()
        if not spot:
            flash("No available spots in this lot.", "warning")
            conn.close()
            return redirect(url_for('user_dashboard'))
        spot_id = spot['id']
        # Book the spot
        conn.execute("INSERT INTO reservations (user_id, spot_id, vehicle_no, checkin_time) VALUES (?, ?, ?, ?)", 
                     (user_id, spot_id, vehicle_no, datetime.now()))
        conn.execute("UPDATE parking_spot SET is_booked = 1 WHERE id = ?", (spot_id,))
        conn.commit()
        conn.close()
        flash("Parking spot booked successfully.", "success")
    except Exception as e:
        print("Booking Error:", e)  # Debug log
        flash("An unexpected error occurred while booking.", "danger")
    return redirect(url_for('user_dashboard'))



@app.route('/user/release/<int:reservation_id>', methods=['POST'])
def release_parking(reservation_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT spot_id, checkout_time FROM reservations WHERE id = ?", (reservation_id,))
    row = cursor.fetchone()
    if not row:
        flash("Reservation not found.", "danger")
        return redirect(url_for('user_dashboard'))
    if row['checkout_time']:
        flash("Spot already released.", "warning")
        return redirect(url_for('user_dashboard'))
    checkout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE reservations SET checkout_time = ? WHERE id = ?", (checkout_time, reservation_id))
    cursor.execute("UPDATE parking_spot SET is_booked = 0 WHERE id = ?", (row['spot_id'],))
    conn.commit()
    conn.close()
    flash("Spot released successfully!", "success")
    return redirect(url_for('user_dashboard'))



@app.route('/admin/summary')
def summary():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    total_lots = conn.execute("SELECT COUNT(*) FROM parking_lots").fetchone()[0]
    total_spots = conn.execute("SELECT COUNT(*) FROM parking_spot").fetchone()[0]
    occupied_spots = conn.execute("SELECT COUNT(*) FROM parking_spot WHERE is_booked = 1").fetchone()[0]
    total_reservations = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    active_reservations = conn.execute("SELECT COUNT(*) FROM reservations WHERE checkout_time IS NULL").fetchone()[0]
    conn.close()
    return render_template('summary.html',
        total_lots=total_lots,
        total_spots=total_spots,
        occupied_spots=occupied_spots,
        total_reservations=total_reservations,
        active_reservations=active_reservations
    )



if __name__ == "__main__":
    app.run(debug=True)
