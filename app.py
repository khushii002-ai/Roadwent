"""
RoadRent - Online Car Rental System (multi-page)
MCA Second Year Project | Flask + Jinja2 templates + SQLite + REST API + JavaScript
All files sit in ONE folder (templates and assets are served from it).
"""
import os
import re
import sqlite3
from datetime import date, datetime
from functools import wraps
from urllib.parse import quote
from flask import (Flask, abort, g, jsonify, redirect, render_template,
                   request, send_from_directory, session)
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "roadrent_v2.db")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@roadrent.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
TYPES = ["Hatchback", "Sedan", "SUV", "Van"]

app = Flask(__name__, template_folder=BASE, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")


# ---------------- database ----------------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer');
    CREATE TABLE IF NOT EXISTS cars(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, type TEXT NOT NULL,
        seats INTEGER NOT NULL, transmission TEXT NOT NULL, fuel TEXT NOT NULL,
        price_per_day INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT, car_id INTEGER NOT NULL REFERENCES cars(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        customer TEXT NOT NULL, phone TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
        days INTEGER NOT NULL, discount INTEGER NOT NULL, total INTEGER NOT NULL,
        status TEXT DEFAULT 'confirmed', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    if conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0] == 0:
        conn.executemany("INSERT INTO cars(name,type,seats,transmission,fuel,price_per_day) VALUES(?,?,?,?,?,?)", [
            ("Maruti Swift", "Hatchback", 5, "Manual", "Petrol", 1500),
            ("Hyundai i20", "Hatchback", 5, "Automatic", "Petrol", 1800),
            ("Honda City", "Sedan", 5, "Automatic", "Petrol", 2500),
            ("Hyundai Verna", "Sedan", 5, "Manual", "Diesel", 2300),
            ("Mahindra XUV700", "SUV", 7, "Automatic", "Diesel", 4200),
            ("Toyota Innova Crysta", "SUV", 7, "Manual", "Diesel", 3800),
            ("Tata Nexon EV", "SUV", 5, "Automatic", "Electric", 3000),
            ("Force Traveller", "Van", 12, "Manual", "Diesel", 5500),
        ])
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute("INSERT INTO users(name,email,phone,password_hash,role) VALUES(?,?,?,?,?)",
                     ("Administrator", ADMIN_EMAIL, "9000000000", generate_password_hash(ADMIN_PASSWORD), "admin"))
    conn.commit()
    conn.close()


# ---------------- business logic ----------------
def parse(d):
    return datetime.strptime(d, "%Y-%m-%d").date()


def discount_for(days):
    """3-6 days = 5% off, 7+ days = 10% off."""
    return 10 if days >= 7 else 5 if days >= 3 else 0


def is_free(car_id, start, end):
    """Two bookings clash when start1 <= end2 AND end1 >= start2."""
    n = db().execute("SELECT COUNT(*) n FROM bookings WHERE car_id=? AND status='confirmed' "
                     "AND start_date<=? AND end_date>=?", (car_id, end, start)).fetchone()["n"]
    return n == 0


def valid_range(start, end):
    try:
        s, e = parse(start), parse(end)
    except (TypeError, ValueError):
        return None, "Choose valid pick-up and return dates."
    if s < date.today():
        return None, "Pick-up date cannot be in the past."
    if e < s:
        return None, "Return date must be on or after the pick-up date."
    days = (e - s).days + 1
    return (None, "You can rent a car for at most 30 days.") if days > 30 else (days, None)


def ref_of(i):
    return f"RR{1000 + i}"


BOOK_SQL = "SELECT b.*, c.name car_name, c.type car_type FROM bookings b JOIN cars c ON c.id=b.car_id "


def booking_json(r):
    return dict(r, ref=ref_of(r["id"]))


def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    return db().execute("SELECT id,name,email,phone,role FROM users WHERE id=?", (uid,)).fetchone()


@app.context_processor
def inject_user():
    return {"user": current_user()}


def page_guard(role=None):
    """Page routes: send visitors to /login (remembering where they wanted to go)."""
    def deco(fn):
        @wraps(fn)
        def inner(*a, **k):
            u = current_user()
            if not u:
                return redirect("/login?next=" + quote(request.full_path.rstrip("?"), safe=""))
            if role and u["role"] != role:
                return redirect("/")
            return fn(*a, **k)
        return inner
    return deco


def api_user(role=None):
    u = current_user()
    if not u:
        abort(401)
    if role and u["role"] != role:
        abort(403)
    return u


@app.errorhandler(401)
def unauthorized(_):
    return jsonify(error="Please log in first."), 401


@app.errorhandler(403)
def forbidden(_):
    return jsonify(error="You do not have permission to do that."), 403


# ---------------- pages (one template per purpose) ----------------
@app.route("/")
def home():
    return render_template("home.html", page="home")


@app.route("/cars")
def cars_page():
    return render_template("cars.html", page="cars")


@app.route("/book")
@page_guard()
def book_page():
    return render_template("book.html", page="cars")


@app.route("/confirmation")
@page_guard()
def confirmation_page():
    return render_template("confirmation.html", page="cars")


@app.route("/my-bookings")
@page_guard()
def mine_page():
    return render_template("mine.html", page="mine")


@app.route("/about")
def about_page():
    return render_template("about.html", page="about")


@app.route("/login")
def login_page():
    return redirect("/") if current_user() else render_template("login.html", page="login")


@app.route("/register")
def register_page():
    return redirect("/") if current_user() else render_template("register.html", page="register")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/admin")
@page_guard("admin")
def admin_page():
    return render_template("admin.html", page="admin")


@app.route("/admin/fleet")
@page_guard("admin")
def fleet_page():
    return render_template("fleet.html", page="admin")


@app.route("/assets/<f>")
def assets(f):
    if f in ("style.css", "app.js"):
        return send_from_directory(BASE, f)
    abort(404)


# ---------------- REST API ----------------
@app.get("/api/cars")
def cars():
    q, p = "SELECT * FROM cars WHERE 1=1", []
    if request.args.get("type"):
        q += " AND type=?"; p.append(request.args["type"])
    if request.args.get("seats"):
        q += " AND seats>=?"; p.append(int(request.args["seats"]))
    if request.args.get("max_price"):
        q += " AND price_per_day<=?"; p.append(int(request.args["max_price"]))
    out = [dict(r) for r in db().execute(q + " ORDER BY price_per_day", p)]
    s, e = request.args.get("start"), request.args.get("end")
    if s and e:
        days, err = valid_range(s, e)
        if err:
            return jsonify(error=err), 400
        for c in out:
            c["available"], c["days"] = is_free(c["id"], s, e), days
    return jsonify(out)


@app.get("/api/cars/<int:cid>")
def one_car(cid):
    r = db().execute("SELECT * FROM cars WHERE id=?", (cid,)).fetchone()
    return jsonify(dict(r)) if r else (jsonify(error="Car not found."), 404)


@app.post("/api/bookings")
def book():
    u = api_user()
    d = request.get_json(force=True)
    days, err = valid_range(d.get("start"), d.get("end"))
    if err:
        return jsonify(error=err), 400
    car = db().execute("SELECT * FROM cars WHERE id=?", (d.get("car_id"),)).fetchone()
    if not car:
        return jsonify(error="Car not found."), 404
    if not is_free(car["id"], d["start"], d["end"]):
        return jsonify(error="Sorry, this car is already booked for those dates."), 409
    disc = discount_for(days)
    total = round(days * car["price_per_day"] * (100 - disc) / 100)
    cur = db().execute("INSERT INTO bookings(car_id,user_id,customer,phone,start_date,end_date,days,discount,total) "
                       "VALUES(?,?,?,?,?,?,?,?,?)", (car["id"], u["id"], u["name"], u["phone"], d["start"], d["end"], days, disc, total))
    db().commit()
    return jsonify(ok=True, ref=ref_of(cur.lastrowid)), 201


@app.get("/api/bookings")
def my_bookings():
    u = api_user()
    rows = db().execute(BOOK_SQL + "WHERE b.user_id=? ORDER BY b.start_date DESC", (u["id"],)).fetchall()
    return jsonify([booking_json(r) for r in rows])


@app.get("/api/bookings/<ref>")
def one_booking(ref):
    u = api_user()
    m = re.fullmatch(r"RR(\d+)", ref.upper())
    r = db().execute(BOOK_SQL + "WHERE b.id=?", (int(m.group(1)) - 1000,)).fetchone() if m else None
    if not r or (r["user_id"] != u["id"] and u["role"] != "admin"):
        return jsonify(error="Booking not found."), 404
    return jsonify(booking_json(r))


@app.post("/api/bookings/<int:bid>/cancel")
def cancel(bid):
    u = api_user()
    b = db().execute("SELECT * FROM bookings WHERE id=?", (bid,)).fetchone()
    if not b or (b["user_id"] != u["id"] and u["role"] != "admin"):
        return jsonify(error="Booking not found."), 404
    if parse(b["start_date"]) <= date.today():
        return jsonify(error="Trips that have started cannot be cancelled."), 400
    db().execute("UPDATE bookings SET status='cancelled' WHERE id=?", (bid,))
    db().commit()
    return jsonify(ok=True)


# ----- accounts -----
@app.post("/api/register")
def register():
    d = request.get_json(force=True)
    name, email, phone = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower(), (d.get("phone") or "").strip()
    pw = d.get("password") or ""
    if len(name) < 3:
        return jsonify(error="Enter your full name."), 400
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify(error="Enter a valid email address."), 400
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        return jsonify(error="Enter a valid 10-digit Indian mobile number."), 400
    if not 6 <= len(pw) <= 72:
        return jsonify(error="Password must be 6 to 72 characters."), 400
    if pw != d.get("confirm"):
        return jsonify(error="Passwords do not match."), 400
    try:
        cur = db().execute("INSERT INTO users(name,email,phone,password_hash) VALUES(?,?,?,?)",
                           (name, email, phone, generate_password_hash(pw)))
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="An account with this email already exists."), 409
    session.clear()
    session["uid"] = cur.lastrowid
    return jsonify(ok=True, role="customer"), 201


@app.post("/api/login")
def login():
    d = request.get_json(force=True)
    u = db().execute("SELECT * FROM users WHERE email=?", ((d.get("email") or "").strip().lower(),)).fetchone()
    if not u or not check_password_hash(u["password_hash"], d.get("password") or ""):
        return jsonify(error="Invalid email or password."), 401  # same message for both cases on purpose
    session.clear()
    session["uid"] = u["id"]
    return jsonify(ok=True, role=u["role"], name=u["name"])


@app.get("/api/me")
def me():
    u = current_user()
    return jsonify(user=dict(u) if u else None)


@app.get("/api/admin/bookings")
def admin_bookings():
    api_user("admin")
    return jsonify([booking_json(r) for r in db().execute(BOOK_SQL + "ORDER BY b.id DESC")])


@app.post("/api/admin/cars")
def add_car():
    api_user("admin")
    d = request.get_json(force=True)
    try:
        seats, price = int(d.get("seats")), int(d.get("price_per_day"))
    except (TypeError, ValueError):
        return jsonify(error="Seats and price must be numbers."), 400
    if not (d.get("name") or "").strip() or d.get("type") not in TYPES:
        return jsonify(error="Enter a car name and choose a type."), 400
    if not (2 <= seats <= 20 and 500 <= price <= 50000):
        return jsonify(error="Seats must be 2-20 and price 500-50000 per day."), 400
    db().execute("INSERT INTO cars(name,type,seats,transmission,fuel,price_per_day) VALUES(?,?,?,?,?,?)",
                 (d["name"].strip(), d["type"], seats, d.get("transmission", "Manual"), d.get("fuel", "Petrol"), price))
    db().commit()
    return jsonify(ok=True), 201


@app.get("/api/stats")
def stats():
    n = lambda sql: db().execute(sql).fetchone()[0]
    return jsonify(cars=n("SELECT COUNT(*) FROM cars"),
                   trips=n("SELECT COUNT(*) FROM bookings WHERE status='confirmed'"),
                   active=n("SELECT COUNT(*) FROM bookings WHERE status='confirmed' AND end_date>=date('now')"),
                   revenue=n("SELECT COALESCE(SUM(total),0) FROM bookings WHERE status='confirmed'"))


init_db()  # runs on import too, so gunicorn (Render, Railway) creates the database on start

if __name__ == "__main__":
    app.run(debug=True)
