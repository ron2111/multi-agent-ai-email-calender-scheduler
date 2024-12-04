# test_gmail_api.py
import os
import base64
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Gmail API SCOPES
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def test_gmail_api():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                logger.error("credentials.json file not found.")
                return
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    # Fetch unread messages
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])

    if not messages:
        logger.info("No new emails.")
        return

    for msg in messages:
        msg_id = msg['id']
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        subject = ""
        from_email = ""
        for header in headers:
            if header['name'].lower() == 'subject':
                subject = header['value']
            if header['name'].lower() == 'from':
                from_email = header['value']

        # Extract the body
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

        logger.info(f"Email from {from_email}, Subject: {subject}")
        logger.info(f"Body: {body}")

        # Example: Send a simple response
        send_response_email(service, subject, from_email, "This is a test response.")

        # Mark the email as read
        service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()

def send_response_email(service, subject, to_email, body_text):
    try:
        message = MIMEMultipart()
        message['To'] = to_email
        message['Subject'] = "Re: " + subject
        message.attach(MIMEText(body_text, 'plain'))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {'raw': raw_message}

        service.users().messages().send(userId='me', body=message_body).execute()
        logger.info(f"Test response email sent to {to_email}")
    except Exception as e:
        logger.error(f"Error sending test response email: {e}")

if __name__ == "__main__":
    test_gmail_api()
