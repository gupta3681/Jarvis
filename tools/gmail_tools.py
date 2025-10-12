"""
Gmail integration tools for Jarvis.

This module provides tools to interact with Gmail API:
- Search emails
- Read email content
- Send emails
- Reply to emails
"""

import os
import pickle
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Path to store credentials (reuse calendar credentials)
TOKEN_PATH = os.path.expanduser('~/.jarvis/gmail_token.pickle')
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'calendar_credentials.json')


def get_gmail_service():
    """
    Get authenticated Gmail service.
    
    Returns:
        Gmail API service object
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
                    f"Google credentials not found at {CREDENTIALS_PATH}\n"
                    "Please download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)


def search_emails_tool(
    query: str = None,
    sender: str = None,
    subject: str = None,
    max_results: int = 10,
    unread_only: bool = False
) -> List[Dict]:
    """
    Search for emails in Gmail.
    
    Args:
        query: General search query (Gmail search syntax)
        sender: Filter by sender email
        subject: Filter by subject
        max_results: Maximum number of results (default: 10)
        unread_only: Only show unread emails
    
    Returns:
        List of email dictionaries with id, sender, subject, snippet, date
    """
    try:
        service = get_gmail_service()
        
        # Build search query
        search_parts = []
        if query:
            search_parts.append(query)
        if sender:
            search_parts.append(f"from:{sender}")
        if subject:
            search_parts.append(f"subject:{subject}")
        if unread_only:
            search_parts.append("is:unread")
        
        search_query = " ".join(search_parts) if search_parts else None
        
        # Search for messages
        results = service.users().messages().list(
            userId='me',
            q=search_query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return []
        
        # Get details for each message
        email_list = []
        for msg in messages:
            try:
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = message['payload']['headers']
                email_data = {
                    'id': msg['id'],
                    'thread_id': message.get('threadId'),
                    'snippet': message.get('snippet', ''),
                    'sender': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                    'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                    'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                }
                email_list.append(email_data)
            except Exception as e:
                print(f"Error getting message {msg['id']}: {e}")
                continue
        
        return email_list
    
    except FileNotFoundError as e:
        raise e
    except HttpError as e:
        raise Exception(f"Gmail API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error searching emails: {str(e)}")


def get_email_content_tool(email_id: str) -> Dict:
    """
    Get full content of an email.
    
    Args:
        email_id: Gmail message ID
    
    Returns:
        Dictionary with email details including body
    """
    try:
        service = get_gmail_service()
        
        # Get the message
        message = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        # Extract headers
        headers = message['payload']['headers']
        email_data = {
            'id': email_id,
            'thread_id': message.get('threadId'),
            'sender': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
            'to': next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown'),
            'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
            'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
            'body': ''
        }
        
        # Extract body
        def get_body(payload):
            """Recursively extract email body."""
            if 'body' in payload and 'data' in payload['body']:
                return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    elif part['mimeType'] == 'text/html':
                        # Fallback to HTML if no plain text
                        if 'data' in part['body']:
                            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    elif 'parts' in part:
                        # Recursive for nested parts
                        body = get_body(part)
                        if body:
                            return body
            return ''
        
        email_data['body'] = get_body(message['payload'])
        
        return email_data
    
    except FileNotFoundError as e:
        raise e
    except HttpError as e:
        raise Exception(f"Gmail API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error getting email content: {str(e)}")


def send_email_tool(
    to: str,
    subject: str,
    body: str,
    cc: str = None,
    bcc: str = None
) -> Dict:
    """
    Send a new email.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
    
    Returns:
        Dictionary with sent message details
    """
    try:
        service = get_gmail_service()
        
        # Create message
        message = MIMEMultipart()
        message['To'] = to
        message['Subject'] = subject
        if cc:
            message['Cc'] = cc
        if bcc:
            message['Bcc'] = bcc
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send message
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return {
            'id': sent_message['id'],
            'thread_id': sent_message.get('threadId'),
            'to': to,
            'subject': subject,
            'status': 'sent'
        }
    
    except FileNotFoundError as e:
        raise e
    except HttpError as e:
        raise Exception(f"Gmail API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error sending email: {str(e)}")


def reply_to_email_tool(
    email_id: str,
    body: str,
    reply_all: bool = False
) -> Dict:
    """
    Reply to an existing email.
    
    Args:
        email_id: Gmail message ID to reply to
        body: Reply body (plain text)
        reply_all: Reply to all recipients (default: False)
    
    Returns:
        Dictionary with sent reply details
    """
    try:
        service = get_gmail_service()
        
        # Get original message
        original = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        headers = original['payload']['headers']
        
        # Extract original details
        original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        original_to = next((h['value'] for h in headers if h['name'] == 'To'), '')
        original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        original_message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        thread_id = original.get('threadId')
        
        # Create reply
        message = MIMEMultipart()
        message['To'] = original_from
        
        if reply_all:
            # Add all original recipients except yourself
            message['Cc'] = original_to
        
        # Add Re: to subject if not already there
        if not original_subject.startswith('Re:'):
            message['Subject'] = f"Re: {original_subject}"
        else:
            message['Subject'] = original_subject
        
        # Add reference headers for threading
        message['In-Reply-To'] = original_message_id
        message['References'] = original_message_id
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send reply
        sent_message = service.users().messages().send(
            userId='me',
            body={
                'raw': raw_message,
                'threadId': thread_id
            }
        ).execute()
        
        return {
            'id': sent_message['id'],
            'thread_id': sent_message.get('threadId'),
            'to': original_from,
            'subject': message['Subject'],
            'status': 'sent'
        }
    
    except FileNotFoundError as e:
        raise e
    except HttpError as e:
        raise Exception(f"Gmail API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error replying to email: {str(e)}")
