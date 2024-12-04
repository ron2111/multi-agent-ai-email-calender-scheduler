import pytest
from agents import schedule_meeting, reschedule_meeting, resolve_conflict, learn_from_feedback, email_handler
import ray
import sqlite3
import json

@pytest.fixture(scope="session", autouse=True)
def initialize_ray():
    ray.init(ignore_reinit_error=True)
    yield
    ray.shutdown()

@pytest.fixture(scope="module")
def setup_database():
    # Initialize the database and insert a test meeting
    conn = sqlite3.connect('scheduler.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO meetings (title, date, time, attendees, status)
        VALUES (?, ?, ?, ?, 'scheduled')
    ''', ("Test Meeting", "2024-12-05", "15:00", "test@example.com"))
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

def test_schedule_meeting():
    text = "Schedule a meeting with Alex next Tuesday at 3 PM."
    future = schedule_meeting.remote(text)
    result = ray.get(future)
    assert "scheduled" in result.lower()

def test_reschedule_meeting(setup_database):
    meeting_id = setup_database
    text = json.dumps({
        "intent": "reschedule",
        "meeting_id": meeting_id,
        "new_date": "2024-12-06",
        "new_time": "16:00"
    })
    future = reschedule_meeting.remote(text)
    result = ray.get(future)
    assert "rescheduled" in result.lower()

def test_reschedule_nonexistent_meeting():
    text = json.dumps({
        "intent": "reschedule",
        "meeting_id": 9999,
        "new_date": "2024-12-06",
        "new_time": "16:00"
    })
    future = reschedule_meeting.remote(text)
    result = ray.get(future)
    assert "does not exist" in result.lower()

def test_resolve_conflict(setup_database):
    meeting_id = setup_database
    # First, schedule another meeting at the same time to create a conflict
    conn = sqlite3.connect('scheduler.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO meetings (title, date, time, attendees, status)
        VALUES (?, ?, ?, ?, 'scheduled')
    ''', ("Conflict Meeting", "2024-12-05", "16:00", "conflict@example.com"))
    conn.commit()
    conflict_meeting_id = cursor.lastrowid
    conn.close()
    
    # Now, try to reschedule the original meeting to a time that conflicts
    result = ray.get(resolve_conflict.remote(meeting_id, "2024-12-05", "16:00"))
    assert "conflict detected" in result.lower()
    
    # Cleanup
    conn = sqlite3.connect('scheduler.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM meetings WHERE id = ?', (conflict_meeting_id,))
    conn.commit()
    conn.close()

def test_learn_from_feedback(setup_database):
    meeting_id = setup_database
    future = learn_from_feedback.remote(meeting_id, 5, "Great scheduling!")
    result = ray.get(future)
    assert "successfully" in result.lower()

def test_email_handler():
    # Note: This test requires a valid Gmail API setup with test emails.
    # For unit testing, consider mocking the Gmail API responses.
    result = ray.get(email_handler.remote())
    assert isinstance(result, str)
