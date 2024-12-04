from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ray
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
    'https://www.googleapis.com/auth/gmail.modify'
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
def startup_event():
    """Start background thread for email listener."""
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            raise ValueError("Invalid Gmail credentials.")
        
        service = build('gmail', 'v1', credentials=creds)
        initialize_history_id(service)

        def email_listener():
            while True:
                fetch_new_emails(service)
                time.sleep(10)  # Poll every 10 seconds

        listener_thread = threading.Thread(target=email_listener, daemon=True)
        listener_thread.start()
        logger.info("Started email listener thread.")
    except Exception as e:
        logger.error(f"Error starting email listener thread: {e}")
