from os import path
from pickle import Unpickler

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    print("\n\033[1;96mtoken.json\033[m file exists")
# If there are no (valid) credentials available, let the user log in.

# Convert Token Pickle to Token Json
if path.exists('token.pickle'):
    with open('token.pickle', "rb") as f:
        unpickler = Unpickler(f)
        creds = unpickler.load()
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("\nGenerated \033[1;96mtoken.json\033[m file from token.pickle")
    exit(1)

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
    print("\nGenerated \033[1;96mtoken.json\033[m file")
