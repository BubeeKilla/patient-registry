from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import psycopg2
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


load_dotenv()

app = Flask(__name__)
app.secret_key = '4bfbbef96d464931f13e474c6c8f0717'

def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Login required.", "warning")
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapped_view

# Connection helper
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME_PG", "patients"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres123")
    )

# Init table
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Create patients table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            condition TEXT
        )
    ''')

    # Create users table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Retry logic
def init_db_with_retry(retries=10, delay=5):
    for attempt in range(retries):
        try:
            init_db()
            print("✅ DB initialized successfully.")
            return
        except Exception as e:
            print(f"⚠️ DB init failed (attempt {attempt+1}): {e}")
            time.sleep(delay)
    raise Exception("❌ Failed to initialize DB after retries.")

@app.before_request
def session_timeout():
    if request.endpoint == 'session_status':
        return
    timeout = timedelta(minutes=2)
    now = datetime.now(timezone.utc).timestamp()
    if 'last_activity' in session:
        last_active = float(session['last_activity'])
        if now - last_active > timeout.total_seconds():
            session.clear()
            flash('Logged out due to inactivity.', 'warning')
            return redirect(url_for('login'))
    session['last_activity'] = now

@app.route('/session-status')
def session_status():
    if 'last_activity' in session:
        now = datetime.now(timezone.utc).timestamp()
        last_active = float(session.get('last_activity'))
        remaining = int(120 - (now - last_active))
        return jsonify({'remaining': max(remaining, 0)})
    return jsonify({'remaining': 0})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash("Username and password required.", "warning")
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)
        conn = get_conn()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
            conn.commit()
            flash("User registered successfully!", "success")
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("Username already exists.", "danger")
        finally:
            conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        result = c.fetchone()
        conn.close()

        if result and check_password_hash(result[0], password):
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))

        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if not session.get('logged_in'):
        flash('Please log in to access the patient registry.', 'danger')
        return redirect(url_for('login'))

    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'asc')
    page = int(request.args.get('page', 1))
    per_page = 5
    allowed_sort_fields = ['id', 'name', 'age', 'condition']
    if sort not in allowed_sort_fields:
        sort = 'id'
    if order not in ['asc', 'desc']:
        order = 'asc'

    offset = (page - 1) * per_page
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM patients")
    total = c.fetchone()[0]

    query = f"SELECT * FROM patients ORDER BY {sort} {order} LIMIT %s OFFSET %s"
    c.execute(query, (per_page, offset))
    patients = c.fetchall()
    conn.close()
    total_pages = (total + per_page - 1) // per_page
    return render_template('index.html', patients=patients, sort=sort, order=order, page=page, total_pages=total_pages)

@app.route('/search')
@login_required
def search():
    if not session.get('logged_in'):
        flash('Please log in to search patients.', 'danger')
        return redirect(url_for('login'))

    search_term = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 5
    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'asc')
    allowed_sort_fields = ['id', 'name', 'age', 'condition']
    if sort not in allowed_sort_fields:
        sort = 'id'
    if order not in ['asc', 'desc']:
        order = 'asc'

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM patients WHERE name ILIKE %s OR condition ILIKE %s", (f"%{search_term}%", f"%{search_term}%"))
    total = c.fetchone()[0]

    offset = (page - 1) * per_page
    query = f"SELECT * FROM patients WHERE name ILIKE %s OR condition ILIKE %s ORDER BY {sort} {order} LIMIT %s OFFSET %s"
    c.execute(query, (f"%{search_term}%", f"%{search_term}%", per_page, offset))
    patients = c.fetchall()
    conn.close()
    total_pages = (total + per_page - 1) // per_page
    return render_template('searchresults.html', patients=patients, search_term=search_term, page=page, total_pages=total_pages, sort=sort, order=order)

@app.route('/add', methods=['POST'])
@login_required
def add():
    if not session.get('logged_in'):
        flash('Please log in to add patients.', 'danger')
        return redirect(url_for('login'))

    name = request.form['name']
    age = request.form['age']
    condition = request.form['condition']
    if not name or not age or not condition:
        flash('All fields are required.', 'warning')
        return redirect(url_for('index'))

    try:
        age = int(age)
        if age <= 0:
            flash("Age must be a positive number.", "info")
            return redirect(url_for('index'))
    except ValueError:
        flash('Age must be a number.', 'info')
        return redirect(url_for('index'))

    if len(name) > 100 or len(condition) > 100:
        flash("Name and condition must be under 100 characters.", "warning")
        return redirect(url_for('index'))

    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT INTO patients (name, age, condition) VALUES (%s, %s, %s)', (name, age, condition))
    conn.commit()
    conn.close()
    flash("Patient added.", "success")
    return redirect(url_for('index'))

@app.route('/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit(patient_id):
    if not session.get('logged_in'):
        flash('Please log in to edit patients.', 'danger')
        return redirect(url_for('login'))

    conn = get_conn()
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        condition = request.form['condition']
        if not name or not age or not condition:
            flash('All fields are required.', 'warning')
            return redirect(url_for('edit', patient_id=patient_id))

        try:
            age = int(age)
            if age <= 0:
                flash("Age must be a positive number.", "info")
                return redirect(url_for('edit', patient_id=patient_id))
        except ValueError:
            flash("Age must be a number.", "warning")
            return redirect(url_for('edit', patient_id=patient_id))

        if len(name) > 100 or len(condition) > 100:
            flash("Name and condition must be under 100 characters.", "info")
            return redirect(url_for('edit', patient_id=patient_id))

        c.execute('UPDATE patients SET name = %s, age = %s, condition = %s WHERE id = %s', (name, age, condition, patient_id))
        conn.commit()
        conn.close()
        flash("Patient updated successfully!", "info")
        return redirect(url_for('index'))

    c.execute('SELECT * FROM patients WHERE id = %s', (patient_id,))
    patient = c.fetchone()
    conn.close()
    return render_template('edit.html', patient=patient)

@app.route('/delete/<int:patient_id>')
@login_required
def delete(patient_id):
    if not session.get('logged_in'):
        flash('Please log in to delete patients.', 'danger')
        return redirect(url_for('login'))

    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM patients WHERE id = %s', (patient_id,))
    conn.commit()
    conn.close()
    flash("Patient deleted.", 'danger')
    return redirect(url_for('index'))

if __name__ == "__main__":
    init_db_with_retry()
    app.run(host="0.0.0.0", port=5000)
