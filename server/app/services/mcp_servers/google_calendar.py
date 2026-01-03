import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("google-calendar")

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']

def get_credentials():
    env_token = os.environ.get("GOOGLE_USER_TOKEN")
    if env_token:
        try:
            if env_token.startswith('{'):
                 return Credentials.from_authorized_user_info(json.loads(env_token), SCOPES)
            else:
                 return Credentials(token=env_token)
        except Exception as e:
            logger.error(f"Error loading token from env: {e}")
    return None

def get_calendar_service():
    creds = get_credentials()
    if not creds:
        raise ValueError("No valid credentials found for Google Calendar. Please connect through UI.")
    return build('calendar', 'v3', credentials=creds)

@mcp.tool(description="List upcoming events from Google Calendar.")
def google_calendar_list_events(max_results: int = 10, time_min: str = None) -> str:
    try:
        service = get_calendar_service()
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'
            
        events_result = service.events().list(
            calendarId='primary', timeMin=time_min,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found."

        output = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            output.append(f"- {start}: {event['summary']} (ID: {event['id']})")

        return "\n".join(output)
    except Exception as e:
        return f"Error listing events: {str(e)}"

@mcp.tool(description="Create a new event in Google Calendar.")
def google_calendar_create_event(summary: str, start_time: str, end_time: str, description: str = None, location: str = None) -> str:
    try:
        service = get_calendar_service()
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {str(e)}"

@mcp.tool(description="Delete an event from Google Calendar.")
def google_calendar_delete_event(event_id: str) -> str:
    try:
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Event deleted successfully."
    except Exception as e:
        return f"Error deleting event: {str(e)}"

if __name__ == "__main__":
    mcp.run()
