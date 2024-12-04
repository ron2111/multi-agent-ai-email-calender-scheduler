from fastapi.testclient import TestClient
from main import app
import pytest
import json
import sqlite3

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    # Initialize the database and insert a test meeting
    conn = sqlite3.connect('scheduler.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO meetings (title, date, time, attendees, status)
        VALUES (?, ?, ?, ?, 'scheduled')
    ''', ("API Test Meeting", "2024-12-05", "15:00", "api_test@example.com"))
    conn.commit()
    meeting_id = cursor.lastrowid
    conn.close()
    yield meeting_id
    # Cleanup
    conn = sqlite3.connect('scheduler.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM meetings WHERE id = ?', (meeting_id,))
    cursor.execute('DELETE FROM feedback WHERE meeting_id = ?', (meeting_id,))
    conn.commit()
    conn.close()

def test_schedule_endpoint():
    response = client.post("/schedule", json={"text": "Schedule a meeting with Bob tomorrow at 10 AM."})
    assert response.status_code == 200
    assert "scheduled" in response.json()["message"].lower()

def test_reschedule_endpoint(setup_database):
    meeting_id = setup_database
    reschedule_text = json.dumps({
        "intent": "reschedule",
        "meeting_id": meeting_id,
        "new_date": "2024-12-07",
        "new_time": "11:00"
    })
    response = client.post("/reschedule", json={"text": reschedule_text})
    assert response.status_code == 200
    assert "rescheduled" in response.json()["message"].lower()

def test_cancel_endpoint(setup_database):
    meeting_id = setup_database
    response = client.post("/cancel", json={"meeting_id": meeting_id})
    assert response.status_code == 200
    assert "canceled" in response.json()["message"].lower()

def test_feedback_endpoint(setup_database):
    meeting_id = setup_database
    response = client.post("/feedback", json={"meeting_id": meeting_id, "rating": 5, "comments": "Excellent!"})
    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()
