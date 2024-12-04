# authorize.py

import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Define the scopes needed for Gmail and Google Calendar API access
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'  # Add Google Calendar scope
]

def authorize_google_services():
    """Handles authorization for Gmail and Google Calendar APIs."""
    creds = None
    # Check if token.json exists for authorized credentials
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("token.json already exists. Using existing credentials.")
    
    # If credentials are invalid or expired, re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("credentials.json file not found in the project root.")
            print("Initiating OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials to token.json for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("token.json file created successfully.")
    
    print("Authorization successful.")
    return creds

if __name__ == "__main__":
    authorize_google_services()
