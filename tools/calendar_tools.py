"""
Google Calendar integration tools for Jarvis.

This module provides tools to interact with Google Calendar API:
- Create events
- List events
- Delete events
- Update events
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import Optional
from dateutil import parser as date_parser
from langchain_core.tools import tool

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Path to store credentials
TOKEN_PATH = os.path.expanduser('~/.jarvis/calendar_token.pickle')
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'calendar_credentials.json')


def get_calendar_service():
    """
    Get authenticated Google Calendar service.
    
    Returns:
        Google Calendar API service object
    """
    creds = None
    
    # Create .jarvis directory if it doesn't exist
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    
    # Load existing credentials
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are invalid or don't exist, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Google Calendar credentials not found at {CREDENTIALS_PATH}\n"
                    "Please download OAuth credentials from Google Cloud Console and save them there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)


def parse_datetime(time_str: str, default_duration_minutes: int = 60) -> tuple:
    """
    Parse natural language or ISO format datetime string.
    
    Args:
        time_str: Time string (e.g., "tomorrow at 3pm", "2025-10-15 14:00")
        default_duration_minutes: Default event duration
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    try:
        # Try parsing with dateutil (handles many formats)
        dt = date_parser.parse(time_str, fuzzy=True)
        
        # If no time specified, default to 9am
        if dt.hour == 0 and dt.minute == 0 and "00:00" not in time_str:
            dt = dt.replace(hour=9, minute=0)
        
        start_dt = dt
        end_dt = dt + timedelta(minutes=default_duration_minutes)
        
        return start_dt, end_dt
    
    except Exception as e:
        # Fallback: use current time + 1 hour
        now = datetime.now()
        return now, now + timedelta(minutes=default_duration_minutes)


@tool
def create_calendar_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = None,
    location: str = None
) -> str:
    """
    Create a new event on Google Calendar.
    
    Args:
        title: Event title/summary
        start_time: Start time in natural language or ISO format 
                   (e.g., "tomorrow at 3pm", "2025-10-15 14:00", "next Monday 10am")
        duration_minutes: Event duration in minutes (default: 60)
        description: Optional event description
        location: Optional event location
    
    Returns:
        Success message with event details
    
    Examples:
        - create_calendar_event("Team Meeting", "tomorrow at 2pm", 60)
        - create_calendar_event("Gym Session", "next Monday 6pm", 90, location="LA Fitness")
    """
    try:
        service = get_calendar_service()
        
        # Parse the start time
        start_dt, end_dt = parse_datetime(start_time, duration_minutes)
        
        # Create event body
        event = {
            'summary': title,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/New_York',  # TODO: Make this configurable
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/New_York',
            },
        }
        
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        
        # Create the event
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        return (
            f"✅ Calendar event created successfully!\n"
            f"📅 {title}\n"
            f"🕐 {start_dt.strftime('%A, %B %d at %I:%M %p')}\n"
            f"⏱️ Duration: {duration_minutes} minutes\n"
            f"🔗 Link: {created_event.get('htmlLink')}"
        )
    
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error creating event: {str(e)}"


@tool
def list_calendar_events(
    date: str = "today",
    days_ahead: int = 1
) -> str:
    """
    List events from Google Calendar for a specific date range.
    
    Args:
        date: Date to start from (e.g., "today", "tomorrow", "2025-10-15")
        days_ahead: Number of days to look ahead (default: 1)
    
    Returns:
        Formatted list of events
    
    Examples:
        - list_calendar_events("today")
        - list_calendar_events("tomorrow", 3)
        - list_calendar_events("next Monday", 7)
    """
    try:
        service = get_calendar_service()
        
        # Parse the start date
        if date.lower() == "today":
            start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif date.lower() == "tomorrow":
            start_dt = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_dt, _ = parse_datetime(date)
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        end_dt = start_dt + timedelta(days=days_ahead)
        
        # Get events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_dt.isoformat() + 'Z',
            timeMax=end_dt.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            date_range = f"{start_dt.strftime('%B %d')}"
            if days_ahead > 1:
                date_range += f" - {end_dt.strftime('%B %d')}"
            return f"📅 No events found for {date_range}"
        
        # Format events
        output = f"📅 **Your Schedule ({start_dt.strftime('%B %d')} - {end_dt.strftime('%B %d')})**\n\n"
        
        current_date = None
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_dt = date_parser.parse(start)
            
            # Add date header if it's a new day
            if current_date != event_dt.date():
                current_date = event_dt.date()
                output += f"\n**{event_dt.strftime('%A, %B %d')}**\n"
            
            # Format event
            time_str = event_dt.strftime('%I:%M %p')
            title = event.get('summary', 'Untitled Event')
            location = event.get('location', '')
            
            output += f"  🕐 {time_str} - {title}"
            if location:
                output += f" @ {location}"
            output += f" (ID: {event['id'][:8]}...)\n"
        
        return output
    
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error listing events: {str(e)}"


@tool
def delete_calendar_event(
    event_id: str = None,
    event_title: str = None
) -> str:
    """
    Delete an event from Google Calendar.
    
    Args:
        event_id: Event ID (from list_calendar_events)
        event_title: Event title to search for (if event_id not provided)
    
    Returns:
        Success or error message
    
    Examples:
        - delete_calendar_event(event_id="abc123...")
        - delete_calendar_event(event_title="Team Meeting")
    """
    try:
        service = get_calendar_service()
        
        # If event_title provided, search for the event
        if not event_id and event_title:
            # Search for events with this title in the next 30 days
            now = datetime.now()
            time_max = now + timedelta(days=30)
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                q=event_title,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return f"❌ No event found with title '{event_title}'"
            
            if len(events) > 1:
                output = f"⚠️ Multiple events found with title '{event_title}':\n\n"
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    event_dt = date_parser.parse(start)
                    output += f"  - {event_dt.strftime('%A, %B %d at %I:%M %p')} (ID: {event['id'][:8]}...)\n"
                output += "\nPlease specify the event_id to delete."
                return output
            
            event_id = events[0]['id']
        
        if not event_id:
            return "❌ Please provide either event_id or event_title"
        
        # Delete the event
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        
        return f"✅ Event deleted successfully!"
    
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except HttpError as e:
        if e.resp.status == 404:
            return f"❌ Event not found. It may have already been deleted."
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error deleting event: {str(e)}"


@tool
def update_calendar_event(
    event_id: str,
    new_title: str = None,
    new_time: str = None,
    new_duration: int = None,
    new_description: str = None,
    new_location: str = None
) -> str:
    """
    Update an existing calendar event.
    
    Args:
        event_id: Event ID to update
        new_title: New event title (optional)
        new_time: New start time (optional)
        new_duration: New duration in minutes (optional)
        new_description: New description (optional)
        new_location: New location (optional)
    
    Returns:
        Success or error message
    
    Examples:
        - update_calendar_event("abc123", new_time="tomorrow at 4pm")
        - update_calendar_event("abc123", new_title="Updated Meeting", new_duration=90)
    """
    try:
        service = get_calendar_service()
        
        # Get the existing event
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Update fields
        if new_title:
            event['summary'] = new_title
        
        if new_time:
            start_dt, end_dt = parse_datetime(new_time, new_duration or 60)
            event['start'] = {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/New_York',
            }
            event['end'] = {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/New_York',
            }
        elif new_duration:
            # Update duration only
            start = event['start'].get('dateTime')
            if start:
                start_dt = date_parser.parse(start)
                end_dt = start_dt + timedelta(minutes=new_duration)
                event['end'] = {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/New_York',
                }
        
        if new_description:
            event['description'] = new_description
        
        if new_location:
            event['location'] = new_location
        
        # Update the event
        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event
        ).execute()
        
        return (
            f"✅ Event updated successfully!\n"
            f"📅 {updated_event.get('summary')}\n"
            f"🔗 Link: {updated_event.get('htmlLink')}"
        )
    
    except FileNotFoundError as e:
        return f"❌ {str(e)}"
    except HttpError as e:
        if e.resp.status == 404:
            return f"❌ Event not found."
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error updating event: {str(e)}"
