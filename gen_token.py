import os
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    print("\nThe token.json file exists")

# If the file token.pickle exists and token.json doesn't exist, then
# let it be converted to token.json
if not os.path.exists('token.json') and os.path.exists('token.pickle'):
    with open('token.pickle', "rb") as f:
        creds = pickle.load(f)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("\nConverted the token.pickle file to token.json")

# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("\nGenerated the token.json file")
