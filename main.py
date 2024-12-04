from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ray
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from agents import (
    schedule_meeting,
    reschedule_meeting,
    resolve_conflict,
    learn_from_feedback,
    email_handler,
    initialize_history_id,
    fetch_new_emails
)
import sqlite3
import asyncio
import threading
import time
import logging
import os  # Missing import added
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]



# Initialize Ray once
if not ray.is_initialized():
    ray.init(ignore_reinit_error=True)

app = FastAPI(title="AI Multi-Agent Calendar Scheduler with Email Integration")

# Define request models
class ScheduleRequest(BaseModel):
    text: str

class RescheduleRequest(BaseModel):
    text: str

class CancelRequest(BaseModel):
    meeting_id: int

class FeedbackRequest(BaseModel):
    meeting_id: int
    rating: int
    comments: str

# API Endpoints

@app.post("/schedule")
async def schedule(request: ScheduleRequest):
    result = await schedule_meeting.remote(request.text)
    return {"message": result}

@app.post("/reschedule")
async def reschedule(request: RescheduleRequest):
    result = await reschedule_meeting.remote(request.text)
    return {"message": result}

@app.post("/cancel")
async def cancel(request: CancelRequest):
    try:
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE meetings
            SET status = 'canceled'
            WHERE id = ?
        ''', (request.meeting_id,))
        conn.commit()
        conn.close()
        return {"message": f"Meeting {request.meeting_id} canceled successfully."}
    except Exception as e:
        logger.error(f"Error canceling meeting: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    result = await learn_from_feedback.remote(request.meeting_id, request.rating, request.comments)
    return {"message": result}

@app.post("/process_emails")
async def process_emails():
    """Endpoint to trigger email processing manually."""
    result = await email_handler.remote()
    return {"message": result}

@app.get("/meetings")
def get_meetings():
    """Fetch all meetings."""
    try:
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM meetings')
        meetings = cursor.fetchall()
        conn.close()
        return {"meetings": meetings}
    except Exception as e:
        logger.error(f"Error fetching meetings: {e}")
        raise HTTPException(status_code=500, detail="Error fetching meetings.")

@app.get("/feedback")
def get_feedback():
    """Fetch all feedback."""
    try:
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM feedback')
        feedback = cursor.fetchall()
        conn.close()
        return {"feedback": feedback}
    except Exception as e:
        logger.error(f"Error fetching feedback: {e}")
        raise HTTPException(status_code=500, detail="Error fetching feedback.")

@app.get("/meeting/{meeting_id}")
def get_meeting_details(meeting_id: int):
    """Fetch details of a specific meeting."""
    try:
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,))
        meeting = cursor.fetchone()
        cursor.execute('SELECT * FROM feedback WHERE meeting_id = ?', (meeting_id,))
        feedback = cursor.fetchall()
        conn.close()
        return {"meeting": meeting, "feedback": feedback}
    except Exception as e:
        logger.error(f"Error fetching meeting details: {e}")
        raise HTTPException(status_code=500, detail="Error fetching meeting details.")


# Background Email Processing
def email_processing_loop():
    """Loop to process emails every 5 minutes."""
    while True:
        try:
            result = ray.get(email_handler.remote())
            logger.info(result)
        except Exception as e:
            logger.error(f"Error in background email processing: {e}")
        time.sleep(300)  # Wait for 5 minutes

@app.on_event("startup")
@app.on_event("startup")
def startup_event():
    """Start background thread for email listener."""
    global LATEST_HISTORY_ID
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            raise ValueError("Invalid Gmail credentials.")
        
        # Initialize Gmail and Google Calendar services
        gmail_service = build('gmail', 'v1', credentials=creds)
        calendar_service = build('calendar', 'v3', credentials=creds)
        
        initialize_history_id(gmail_service)

        # Background email listener
        def email_listener():
            while True:
                fetch_new_emails(gmail_service)
                time.sleep(10)  # Poll every 10 seconds

        listener_thread = threading.Thread(target=email_listener, daemon=True)
        listener_thread.start()

        logger.info("Started email listener thread.")
    except Exception as e:
        logger.error(f"Error starting email listener thread: {e}")

