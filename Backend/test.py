# Refer to the Python quickstart on how to setup the environment:
# https://developers.google.com/calendar/quickstart/python
# Change the scope to 'https://www.googleapis.com/auth/calendar' and delete any
# stored credentials.

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    service = build("calendar", "v3", credentials=creds)
    return service


event = {
    "summary": "Google I/O 2015",
    "location": "800 Howard St., San Francisco, CA 94103",
    "description": "A chance to hear more about Google's developer products.",
    "start": {
        "dateTime": "2024-05-28T09:00:00-07:00",
        "timeZone": "America/Los_Angeles",
    },
    "end": {
        "dateTime": "2024-05-28T17:00:00-07:00",
        "timeZone": "America/Los_Angeles",
    },
}

service = get_calendar_service()
event = service.events().insert(calendarId="primary", body=event).execute()
print("Event created: %s" % (event.get("htmlLink")))
