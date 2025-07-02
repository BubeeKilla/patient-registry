from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import logging
import os
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = '4bfbbef96d464931f13e474c6c8f0717'
DB_NAME = os.getenv('DB_NAME', 'patients.db')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure the table exists
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            condition TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.before_request
def session_timeout():
    if request.endpoint == 'session_status':
        return  # Don't refresh timer for countdown AJAX

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
        timeout = 120  # 2 minutes in seconds
        remaining = int(timeout - (now - last_active))
        return jsonify({'remaining': max(remaining, 0)})
    return jsonify({'remaining': 0})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'password':  # Hardcoded for demo
            session['logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
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

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM patients")
    total = c.fetchone()[0]

    query = f"SELECT * FROM patients ORDER BY {sort} {order} LIMIT {per_page} OFFSET {offset}"
    c.execute(query)
    patients = c.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template('index.html', patients=patients, sort=sort, order=order, page=page, total_pages=total_pages)

@app.route('/search')
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

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM patients WHERE name LIKE ? OR condition LIKE ?", (f"%{search_term}%", f"%{search_term}%"))
    total = c.fetchone()[0]

    offset = (page - 1) * per_page
    query = f"SELECT * FROM patients WHERE name LIKE ? OR condition LIKE ? ORDER BY {sort} {order} LIMIT ? OFFSET ?"
    c.execute(query, (f"%{search_term}%", f"%{search_term}%", per_page, offset))
    patients = c.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template('searchresults.html', patients=patients, search_term=search_term, page=page, total_pages=total_pages, sort=sort, order=order)

@app.route('/add', methods=['POST'])
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
    
    logging.info(f"Adding patient: {name}, {age}, {condition}")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO patients (name, age, condition) VALUES (?, ?, ?)', (name, age, condition))
    conn.commit()
    conn.close()
    flash("Patient added.", "success")
    return redirect(url_for('index'))

@app.route('/edit/<int:patient_id>', methods=['GET', 'POST'])
def edit(patient_id):
    if not session.get('logged_in'):
        flash('Please log in to edit patients.', 'danger')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
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
        
        c.execute('UPDATE patients SET name = ?, age = ?, condition = ? WHERE id = ?', (name, age, condition, patient_id))
        conn.commit()
        conn.close()
        logging.info(f"Edited patient ID {patient_id}: {name}, {age}, {condition}")
        flash("Patient updated successfully!", "info")
        return redirect(url_for('index'))

    c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = c.fetchone()
    conn.close()
    return render_template('edit.html', patient=patient)

@app.route('/delete/<int:patient_id>')
def delete(patient_id):
    if not session.get('logged_in'):
        flash('Please log in to delete patients.', 'danger')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    conn.close()
    logging.info(f"Deleted patient with ID: {patient_id}")
    flash("Patient deleted.", "danger")
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
