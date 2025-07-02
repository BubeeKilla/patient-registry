import os
import sys
import sqlite3
import pytest

# Ensure we can import app.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['DB_NAME'] = 'test_patients.db'
from app import app, DB_NAME

@pytest.fixture
def client():
    """Fixture to set up a test client with a logged-in session."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['logged_in'] = True
        yield client

def reset_db():
    """Helper to clear the patients table before each test."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM patients')
    conn.commit()
    conn.close()

def test_index_page(client):
    reset_db()
    response = client.get('/')
    assert response.status_code == 200
    assert b'Patient Registry' in response.data

def test_add_patient(client):
    reset_db()
    client.post('/add', data={
        'name': 'Test User',
        'age': '30',
        'condition': 'Test Condition'
    }, follow_redirects=True)

    response = client.get('/?page=1&per_page=100')
    html = response.data.decode('utf-8')

    assert 'Test User' in html
    assert '30' in html
    assert 'Test Condition' in html

def test_invalid_add(client):
    reset_db()
    response = client.post('/add', data={
        'name': '',
        'age': '',
        'condition': ''
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'All fields are required' in response.data.decode('utf-8')

def test_edit_patient(client):
    reset_db()
    client.post('/add', data={
        'name': 'Old Name',
        'age': '40',
        'condition': 'Old Condition'
    }, follow_redirects=True)

    # Get the patient ID dynamically
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM patients WHERE name = 'Old Name'")
    patient_id = c.fetchone()[0]
    conn.close()

    client.post(f'/edit/{patient_id}', data={
        'name': 'New Name',
        'age': '41',
        'condition': 'Updated Condition'
    }, follow_redirects=True)

    response = client.get('/?page=1&per_page=100')
    html = response.data.decode('utf-8')

    assert 'New Name' in html
    assert '41' in html
    assert 'Updated Condition' in html
    assert 'Old Name' not in html

def test_delete_patient(client):
    reset_db()
    client.post('/add', data={
        'name': 'Delete Me',
        'age': '50',
        'condition': 'Temporary'
    }, follow_redirects=True)

    # Get the patient ID dynamically
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM patients WHERE name = 'Delete Me'")
    patient_id = c.fetchone()[0]
    conn.close()

    client.get(f'/delete/{patient_id}', follow_redirects=True)

    response = client.get('/?page=1&per_page=100')
    html = response.data.decode('utf-8')

    assert 'Delete Me' not in html
