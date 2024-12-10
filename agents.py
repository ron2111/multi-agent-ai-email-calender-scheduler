# agents.py
import openai
import sqlite3
from datetime import datetime, timedelta
import os
import json
import ray
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import re
# agents.py

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import threading

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


LATEST_HISTORY_ID = None

openai_api_key = os.getenv('OPENAI_API_KEY')
# Define Gmail API SCOPES
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

def parse_natural_language(text, sender_email):
    current_datetime = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    prompt = (
        f"Today's date and time is {current_datetime}. "
        "Extract the intent, entities, and attendees from the following text in JSON format. "
        "Interpret 'me' as the sender's email. Also, include a boolean field 'is_sender_required' "
        "to indicate if the sender explicitly wants to be added to the attendees list.\n\n"
        f"Sender Email: {sender_email}\n"
        f"Text: {text}\n\n"
        "Example Output:\n"
        "{\n"
        "  \"intent\": \"schedule\", \n"
        "  \"title\": \"Meeting\", \n"
        "  \"date\": \"2024-12-05\", \n"
        "  \"time\": \"15:00\", \n"
        "  \"attendees\": [\"sender@example.com\", \"ravi@example.com\"],\n"
        "  \"is_sender_required\": true\n"
        "}"
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts intents and entities from text, ensuring attendee information is accurate."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.5,
        )
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```json") and raw_content.endswith("```"):
            raw_content = raw_content[7:-3].strip()

        return raw_content

    except Exception as e:
        logger.error(f"Error parsing natural language: {e}")
        return "{}"

def create_google_calendar_event(creds, title, date, time, attendees):
    """Create an event in Google Calendar."""
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Convert attendees set to a list of dictionaries
        attendees_list = [{'email': attendee} for attendee in attendees]

        event = {
            'summary': title,
            'start': {
                'dateTime': f'{date}T{time}:00',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': f'{date}T{int(time[:2]) + 1}:{time[3:]}:00',  # End time 1 hour later
                'timeZone': 'UTC',
            },
            'attendees': attendees_list,
        }
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Event created: {event_result['summary']}")
        return f"Event created successfully: {event_result.get('htmlLink')}"
    except HttpError as error:
        logger.error(f"Error creating event: {error}")
        return f"Error creating the event in Google Calendar: {error}"


def is_valid_email(email):
    """Simple regex check for valid email."""
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    return re.match(regex, email) is not None

def send_calendar_invitation(service, to_email, event, meeting_id):
    """Send acknowledgment email with a single calendar invitation."""
    try:
        # Convert ISO datetime to human-readable format
        start_time = datetime.strptime(event['start']['dateTime'], "%Y-%m-%dT%H:%M:%S")
        end_time = datetime.strptime(event['end']['dateTime'], "%Y-%m-%dT%H:%M:%S")
        formatted_date = start_time.strftime("%A, %B %d, %Y")
        formatted_time = f"{start_time.strftime('%I:%M %p')} to {end_time.strftime('%I:%M %p')}"

        # Email subject and body
        subject = f"Meeting Confirmation (ID: {meeting_id}): {event['summary']}"
        body = (
            f"Dear {to_email},\n\n"
            f"Your meeting '{event['summary']}' (ID: {meeting_id}) has been scheduled successfully.\n\n"
            f"Details:\n"
            f"Date: {formatted_date}\n"
            f"Time: {formatted_time}\n\n"
            "A calendar invitation has been attached for your convenience."
        )

        # Create email message
        message = MIMEMultipart()
        message['To'] = to_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        # Create ICS data
        ics_data = (
            f"BEGIN:VCALENDAR\n"
            f"VERSION:2.0\n"
            f"BEGIN:VEVENT\n"
            f"SUMMARY:{event['summary']}\n"
            f"DTSTART:{start_time.strftime('%Y%m%dT%H%M%S')}\n"
            f"DTEND:{end_time.strftime('%Y%m%dT%H%M%S')}\n"
            f"LOCATION:Virtual\n"
            f"DESCRIPTION:Scheduled via AI Assistant.\n"
            f"END:VEVENT\n"
            f"END:VCALENDAR"
        )

        # Attach ICS file
        attachment = MIMEText(ics_data, 'calendar; method=REQUEST')
        attachment.add_header('Content-Disposition', 'attachment', filename='invite.ics')
        message.attach(attachment)

        # Encode and send email
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        logger.info(f"Calendar invitation sent to {to_email}")
    except Exception as e:
        logger.error(f"Error sending calendar invitation: {e}")

@ray.remote
def schedule_meeting(text, from_email):
    parsed = parse_natural_language(text, from_email)
    try:
        data = json.loads(parsed)
        intent = data.get('intent', '').lower()
        if intent != 'schedule':
            logger.warning(f"Unrecognized intent: {intent}. Email will not be sent.")
            return f"Intent '{intent}' not recognized for scheduling. No email sent."

        title = data.get('title', 'Meeting')
        date = data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))  # Default to today's date
        time = data.get('time', '09:00')  # Default to 9 AM UTC
        attendees = data.get('attendees', [])
        is_sender_required = data.get('is_sender_required', False)

        # Validate and process attendees
        valid_attendees = set()
        authorized_user_email = os.getenv('AUTHORIZED_USER_EMAIL', 'default_email@domain.com')

        for attendee in attendees:
            attendee = attendee.strip()
            if attendee.lower() == "me":
                valid_attendees.add(authorized_user_email)  # Map "me" to authorized email
            elif is_valid_email(attendee):
                valid_attendees.add(attendee)
            else:
                logger.warning(f"Invalid attendee email or ambiguous reference: {attendee}. Ignoring.")

        # Add the sender's email if 'is_sender_required' is true
        if is_sender_required:
            valid_attendees.add(from_email)

        # Add the default authorized user email if no attendees are valid
        if not valid_attendees:
            valid_attendees.add(authorized_user_email)
            logger.info(f"No valid attendees provided. Using default authorized user email: {authorized_user_email}")

        # Insert meeting into the database
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO meetings (title, date, time, attendees, status)
            VALUES (?, ?, ?, ?, 'scheduled')
        ''', (title, date, time, ','.join(valid_attendees)))
        conn.commit()
        meeting_id = cursor.lastrowid
        conn.close()

        # Integrate with Google Calendar
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        event = {
            "summary": title,
            "start": {"dateTime": f"{date}T{time}:00"},
            "end": {"dateTime": f"{date}T{int(time[:2]) + 1}:{time[3:]}:00"}
        }
        calendar_response = create_google_calendar_event(creds, title, date, time, valid_attendees)

        if "Event created successfully" in calendar_response:
            # Send acknowledgment email
            service = build('gmail', 'v1', credentials=creds)
            send_calendar_invitation(service, from_email, event, meeting_id)
            return f"Meeting '{title}' scheduled on {date} at {time} with attendees: {list(valid_attendees)}. {calendar_response}"
        else:
            return f"Meeting '{title}' scheduled locally but failed to create in Google Calendar: {calendar_response}"

    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from parsed data.")
        return "Failed to parse the meeting details. No email sent."
    except KeyError as e:
        logger.error(f"Missing key in parsed data: {e}")
        return f"Missing key in parsed data: {e}. No email sent."
    except Exception as e:
        logger.error(f"Error scheduling meeting: {e}")
        return f"Error scheduling meeting: {str(e)}. No email sent."

@ray.remote
def reschedule_meeting(text, creds):
    """Reschedule a meeting and update the event on Google Calendar."""
    parsed = parse_natural_language(text)
    try:
        data = json.loads(parsed)
        intent = data.get('intent', '').lower()
        if intent != 'reschedule':
            logger.warning(f"Unrecognized intent: {intent}. Email will not be sent.")
            return f"Intent '{intent}' not recognized for rescheduling. No email sent."
        
        meeting_id = data['meeting_id']
        new_date = data.get('new_date')
        new_time = data.get('new_time')
        
        # Check if meeting exists
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,))
        meeting = cursor.fetchone()
        if not meeting:
            conn.close()
            logger.warning(f"Meeting with ID {meeting_id} does not exist.")
            return f"Meeting with ID {meeting_id} does not exist. No email sent."
        
        # Update the meeting in the database
        cursor.execute('''
            UPDATE meetings
            SET date = ?, time = ?, status = 'rescheduled'
            WHERE id = ?
        ''', (new_date, new_time, meeting_id))
        conn.commit()
        conn.close()

        # Reschedule the event on Google Calendar
        event_id = meeting[0]  # Assuming the event ID in Google Calendar is the same as the meeting ID
        event_result = update_google_calendar_event(creds, event_id, new_date, new_time)
        
        if event_result:
            return f"Meeting {meeting_id} rescheduled to {new_date} at {new_time}."
        else:
            return "Failed to reschedule Google Calendar event."

    except Exception as e:
        logger.error(f"Error rescheduling meeting: {e}")
        return f"Error rescheduling meeting: {str(e)}. No email sent."

def update_google_calendar_event(creds, event_id, new_date, new_time):
    """Update an existing event in Google Calendar."""
    try:
        service = build('calendar', 'v3', credentials=creds)
        event = service.events().get(calendarId='primary', eventId=event_id).execute()

        # Update event time
        event['start']['dateTime'] = f'{new_date}T{new_time}:00'
        event['end']['dateTime'] = f'{new_date}T{int(new_time[:2]) + 1}:{new_time[3:]}:00'

        updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        logger.info(f"Event updated: {updated_event['summary']}")
        return updated_event
    except HttpError as error:
        logger.error(f"Error updating event: {error}")
        return None

def notify_conflict(service, to_email, proposed_time):
    """Notify the sender about a scheduling conflict and propose an alternative time."""
    try:
        message = MIMEMultipart()
        message['To'] = to_email
        message['Subject'] = "Meeting Scheduling Conflict"

        body = (
            f"Dear {to_email},\n\n"
            f"There was a conflict scheduling your meeting. The proposed time is unavailable.\n"
            f"Suggested Alternative: {proposed_time}\n\n"
            "Please let us know if this works for you or propose another time."
        )
        message.attach(MIMEText(body, 'plain'))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        logger.info(f"Conflict notification sent to {to_email}")
    except Exception as e:
        logger.error(f"Error sending conflict notification: {e}")

@ray.remote
def resolve_conflict(meeting_id, proposed_date, proposed_time, from_email):
    try:
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()

        # Check for conflicts
        cursor.execute('''
            SELECT * FROM meetings
            WHERE date = ? AND time = ? AND status = 'scheduled' AND id != ?
        ''', (proposed_date, proposed_time, meeting_id))
        conflicts = cursor.fetchall()

        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        service = build('gmail', 'v1', credentials=creds)

        if conflicts:
            new_time_dt = datetime.strptime(proposed_time, "%H:%M") + timedelta(hours=1)
            proposed_time_new = new_time_dt.strftime("%H:%M")
            notify_conflict(service, from_email, proposed_time_new)
            return f"Conflict detected. Proposed alternative time: {proposed_time_new}."
        else:
            # No conflict, schedule the meeting
            cursor.execute('''
                UPDATE meetings
                SET date = ?, time = ?, status = 'scheduled'
                WHERE id = ?
            ''', (proposed_date, proposed_time, meeting_id))
            conn.commit()
            conn.close()
            return f"Meeting {meeting_id} scheduled on {proposed_date} at {proposed_time}."
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}")
        return f"Error resolving conflict: {str(e)}. No email sent."

@ray.remote
def learn_from_feedback(meeting_id, rating, comments):
    try:
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (meeting_id, rating, comments)
            VALUES (?, ?, ?)
        ''', (meeting_id, rating, comments))
        conn.commit()
        conn.close()
        
        # Placeholder for learning logic
        # Future implementation can adjust preferences based on feedback
        
        return "Feedback recorded successfully."
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        return f"Error recording feedback: {str(e)}. No email sent."

@ray.remote
def email_handler(): 
    """Monitors Gmail inbox for new scheduling emails based on history ID."""
    global LATEST_HISTORY_ID
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    logger.error("credentials.json file not found.")
                    return "credentials.json file not found."
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        service = build('gmail', 'v1', credentials=creds)

        # Check if history ID is initialized
        if not LATEST_HISTORY_ID:
            logger.error("History ID not initialized. Run initialize_history_id first.")
            return "History ID not initialized."

        # Fetch new messages based on history ID
        results = service.users().history().list(
            userId='me',
            startHistoryId=LATEST_HISTORY_ID
        ).execute()

        changes = results.get('history', [])
        if not changes:
            logger.info("No new emails since the last check.")
            return "No new emails."

        for change in changes:
            messages = change.get('messages', [])
            for message in messages:
                msg_id = message['id']
                process_email(service, msg_id)

        # Update the latest history ID
        if 'historyId' in results:
            LATEST_HISTORY_ID = results['historyId']

        return "Processed new emails."
    except Exception as e:
        logger.error(f"Error in email_handler: {e}")
        return f"Error in email_handler: {str(e)}. No email sent."

def send_email(subject, to_email, body, service):
    """Sends an email response."""
    try:
        message = MIMEMultipart()
        message['To'] = to_email
        message['Subject'] = "Re: " + subject
        message.attach(MIMEText(body, 'plain'))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {'raw': raw_message}

        service.users().messages().send(userId='me', body=message_body).execute()
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        
        

def initialize_history_id(service):
    """Initialize the history ID when the server starts."""
    global LATEST_HISTORY_ID
    try:
        # Get the current profile's history ID
        profile = service.users().getProfile(userId='me').execute()
        LATEST_HISTORY_ID = profile.get('historyId')
        logger.info(f"Initialized latest history ID: {LATEST_HISTORY_ID}")
    except Exception as e:
        logger.error(f"Error initializing history ID: {e}")


def fetch_new_emails(service):
    """Fetch new emails using Gmail history API."""
    global LATEST_HISTORY_ID
    try:
        if not LATEST_HISTORY_ID:
            logger.error("History ID not initialized.")
            return

        # Fetch new messages based on history ID
        results = service.users().history().list(
            userId='me', startHistoryId=LATEST_HISTORY_ID
        ).execute()

        changes = results.get('history', [])
        for change in changes:
            messages = change.get('messages', [])
            for message in messages:
                msg_id = message['id']
                process_email(service, msg_id)

        # Update the latest history ID
        if 'historyId' in results:
            LATEST_HISTORY_ID = results['historyId']
    except Exception as e:
        logger.error(f"Error fetching new emails: {e}")

def process_email(service, msg_id):
    """Process a single email by ID."""
    try:
        # Check if the message has already been processed
        conn = sqlite3.connect('scheduler.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM processed_emails WHERE msg_id = ?', (msg_id,))
        if cursor.fetchone():
            logger.info(f"Email {msg_id} has already been processed. Skipping.")
            conn.close()
            return

        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "")
        from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), "")
        # Extract the email address from the 'From' header
        from_email = re.search(r'<(.+?)>', from_email)
        from_email = from_email.group(1) if from_email else from_email

        # Extract the email body
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
                        body += decoded_data
        else:
            data = payload['body'].get('data', '')
            if data:
                decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
                body += decoded_data

        if not body:
            body = "No content found in the email body."

        logger.info(f"Processing email from {from_email} with subject '{subject}'.")
        response_message = ray.get(schedule_meeting.remote(body, from_email))

        logger.info(response_message)

        # Mark the email as processed
        cursor.execute('INSERT INTO processed_emails (msg_id) VALUES (?)', (msg_id,))
        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Error processing email: {e}")

def create_event(creds, title, date, time, attendees):
    try:
        service = build('calendar', 'v3', credentials=creds)
        start_datetime = f"{date}T{time}:00"
        end_time = (datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)).strftime("%H:%M:%S")
        end_datetime = f"{date}T{end_time}"

        event = {
            'summary': title,
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'UTC',
            },
            'attendees': [{'email': attendee} for attendee in attendees],
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Event created: {created_event.get('htmlLink')}")
        return f"Event created successfully: {created_event.get('htmlLink')}"
    except HttpError as error:
        error_content = error.content.decode() if hasattr(error, 'content') else str(error)
        logger.error(f"An error occurred while creating the event: {error_content}")
        return f"Failed to create the event in Google Calendar. Error: {error_content}"
