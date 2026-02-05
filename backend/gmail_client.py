"""
Gmail Client for reading and managing emails.

This module provides functions to read emails, list messages, search,
and download attachments using the Gmail API. It supports manual/on-demand
operations only (no automatic monitoring).

Usage:
    from gmail_client import read_email, list_emails, search_emails

    # Read a specific email
    email = read_email('message_id_123')

    # List recent emails
    emails = list_emails(max_results=10)

    # Search emails
    results = search_emails(from_email='sender@example.com', subject='Invoice')

Requirements:
    - Google OAuth credentials must be set up (run google_auth_setup.py)
    - Gmail API must be enabled in Google Cloud Console
    - Scopes: gmail.readonly, gmail.send
"""

import os
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google_user_credentials.json')
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]


def get_gmail_service():
    """
    Get authenticated Gmail API service.

    Returns:
        Gmail API service resource.

    Raises:
        FileNotFoundError: If credentials file doesn't exist.
        ValueError: If authentication fails.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Credentials file not found: {CREDENTIALS_FILE}\n"
            "Run google_auth_setup.py to authenticate."
        )

    try:
        credentials = Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)

        # Refresh credentials if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        if not credentials.valid:
            raise ValueError("Credentials are not valid. Re-run google_auth_setup.py")

        return build('gmail', 'v1', credentials=credentials)

    except HttpError as error:
        if error.resp.status == 401:
            raise ValueError("Authentication failed. Re-run google_auth_setup.py")
        raise


def parse_headers(headers: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Parse email headers into a dictionary.

    Args:
        headers: List of header dictionaries from Gmail API.

    Returns:
        Dictionary with common headers (from, to, subject, date, etc).

    Example:
        >>> headers = [{'name': 'From', 'value': 'sender@example.com'}]
        >>> result = parse_headers(headers)
        >>> result['from']
        'sender@example.com'
    """
    parsed = {}
    header_map = {
        'from': 'from',
        'to': 'to',
        'cc': 'cc',
        'bcc': 'bcc',
        'subject': 'subject',
        'date': 'date',
        'message-id': 'message_id',
        'in-reply-to': 'in_reply_to',
        'references': 'references',
    }

    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        if name in header_map:
            parsed[header_map[name]] = value

    return parsed


def extract_text_from_payload(payload: Dict[str, Any]) -> str:
    """
    Extract text content from email payload.

    Handles both plain text and multipart emails.

    Args:
        payload: Email payload from Gmail API.

    Returns:
        Extracted text content.

    Example:
        >>> payload = {'mimeType': 'text/plain', 'body': {'data': 'base64...'}}
        >>> text = extract_text_from_payload(payload)
    """
    mime_type = payload.get('mimeType', '')
    body = payload.get('body', {})
    parts = payload.get('parts', [])

    # Handle plain text or HTML directly in body
    if body.get('data'):
        data = body.get('data', '')
        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        return decoded

    # Handle multipart (recursively extract from parts)
    if parts:
        text_parts = []
        for part in parts:
            part_mime = part.get('mimeType', '')
            # Extract text/plain or text/html parts
            if part_mime.startswith('text/'):
                text_parts.append(extract_text_from_payload(part))
            # Recursively handle nested multipart
            elif part_mime.startswith('multipart/'):
                text_parts.append(extract_text_from_payload(part))
        return '\n\n'.join(filter(None, text_parts))

    return ''


def get_attachment_info(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract attachment information from email message.

    Args:
        message: Email message from Gmail API.

    Returns:
        List of attachment info dictionaries containing:
        - filename: Attachment filename
        - mime_type: MIME type
        - attachment_id: ID for downloading
        - size: Size in bytes

    Example:
        >>> message = read_email('msg_id')
        >>> attachments = get_attachment_info(message)
        >>> for att in attachments:
        ...     print(f"{att['filename']} ({att['size']} bytes)")
    """
    attachments = []
    payload = message.get('payload', {})
    parts = payload.get('parts', [])

    def extract_attachments_from_parts(parts_list):
        """Recursively extract attachments from parts."""
        for part in parts_list:
            filename = part.get('filename', '')
            body = part.get('body', {})
            attachment_id = body.get('attachmentId')

            # This part is an attachment
            if filename and attachment_id:
                attachments.append({
                    'filename': filename,
                    'mime_type': part.get('mimeType', ''),
                    'attachment_id': attachment_id,
                    'size': body.get('size', 0),
                })

            # Recursively check nested parts
            nested_parts = part.get('parts', [])
            if nested_parts:
                extract_attachments_from_parts(nested_parts)

    extract_attachments_from_parts(parts)
    return attachments


def read_email(message_id: str) -> Dict[str, Any]:
    """
    Read a specific email by message ID.

    Retrieves full email details including headers, body, and attachment info.

    Args:
        message_id: Gmail message ID.

    Returns:
        Dictionary containing:
        - id: Message ID
        - thread_id: Thread ID
        - labels: List of label IDs
        - snippet: Email snippet
        - subject: Email subject
        - from: Sender email
        - to: Recipient email
        - date: Date string
        - body: Plain text body
        - html_body: HTML body (if available)
        - attachments: List of attachment info

    Raises:
        ValueError: If email not found or authentication fails.
        ConnectionError: If network error occurs.

    Example:
        >>> email = read_email('msg_18f2c3a1b2d4e5f6')
        >>> print(f"From: {email['from']}")
        >>> print(f"Subject: {email['subject']}")
        >>> print(f"Body: {email['body']}")
    """
    try:
        service = get_gmail_service()

        # Get the email
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        # Parse headers
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        parsed_headers = parse_headers(headers)

        # Extract body content
        body_text = ''
        html_body = ''

        # Check if multipart
        if 'parts' in payload:
            for part in payload.get('parts', []):
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    body_text = extract_text_from_payload(part)
                elif mime_type == 'text/html':
                    html_body = extract_text_from_payload(part)
                elif mime_type.startswith('multipart/'):
                    # Handle nested multipart
                    nested_text = extract_text_from_payload(part)
                    if not body_text:
                        body_text = nested_text
        else:
            # Simple email with body directly in payload
            body_text = extract_text_from_payload(payload)

        # Build result
        result = {
            'id': message.get('id'),
            'thread_id': message.get('threadId'),
            'labels': message.get('labelIds', []),
            'snippet': message.get('snippet', ''),
            'subject': parsed_headers.get('subject', ''),
            'from': parsed_headers.get('from', ''),
            'to': parsed_headers.get('to', ''),
            'cc': parsed_headers.get('cc', ''),
            'date': parsed_headers.get('date', ''),
            'message_id': parsed_headers.get('message_id', ''),
            'body': body_text,
            'attachments': get_attachment_info(message),
        }

        # Include HTML body if present
        if html_body:
            result['html_body'] = html_body

        return result

    except HttpError as error:
        if error.resp.status == 404:
            raise ValueError(f"Email not found: {message_id}")
        elif error.resp.status == 401:
            raise ValueError("Authentication failed. Re-run google_auth_setup.py")
        elif error.resp.status == 429:
            raise ValueError("Rate limit exceeded. Please try again later.")
        raise


def list_emails(query: str = '', max_results: int = 10, include_all_pages: bool = False) -> Dict[str, Any]:
    """
    List emails matching a query.

    Args:
        query: Gmail search query (e.g., 'is:unread', 'from:user@example.com').
               Empty string returns all emails.
        max_results: Maximum number of results per page (default: 10).
        include_all_pages: If True, fetch all pages of results (default: False).

    Returns:
        Dictionary containing:
        - messages: List of message objects with 'id' and 'threadId'
        - nextPageToken: Token for next page (if available)
        - resultSizeEstimate: Estimated total results

    Raises:
        ValueError: If authentication fails or rate limit exceeded.

    Example:
        >>> # List unread emails
        >>> result = list_emails(query='is:unread', max_results=5)
        >>> for msg in result['messages']:
        ...     email = read_email(msg['id'])
        ...     print(email['subject'])
    """
    try:
        service = get_gmail_service()

        all_messages = []
        page_token = None

        while True:
            # List messages
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'q': query,
            }
            if page_token:
                request_params['pageToken'] = page_token

            result = service.users().messages().list(**request_params).execute()

            messages = result.get('messages', [])
            all_messages.extend(messages)

            # Check if we should continue pagination
            page_token = result.get('nextPageToken')
            if not include_all_pages or not page_token:
                break

        # Return with all messages
        return {
            'messages': all_messages,
            'resultSizeEstimate': len(all_messages),
        }

    except HttpError as error:
        if error.resp.status == 401:
            raise ValueError("Authentication failed. Re-run google_auth_setup.py")
        elif error.resp.status == 429:
            raise ValueError("Rate limit exceeded. Please try again later.")
        raise


def search_emails(
    from_email: Optional[str] = None,
    to_email: Optional[str] = None,
    subject: Optional[str] = None,
    after_date: Optional[datetime] = None,
    before_date: Optional[datetime] = None,
    has_attachment: bool = False,
    is_unread: bool = False,
    label: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Search emails using common criteria.

    Constructs a Gmail search query from parameters and returns matching emails.

    Args:
        from_email: Filter by sender email.
        to_email: Filter by recipient email.
        subject: Filter by subject (partial match).
        after_date: Only emails after this date.
        before_date: Only emails before this date.
        has_attachment: Only emails with attachments.
        is_unread: Only unread emails.
        label: Filter by label (e.g., 'INBOX', 'SENT').
        max_results: Maximum number of results (default: 10).

    Returns:
        Same as list_emails() - dictionary with 'messages' list.

    Example:
        >>> # Find unread invoices from specific sender
        >>> results = search_emails(
        ...     from_email='billing@example.com',
        ...     subject='Invoice',
        ...     is_unread=True,
        ...     has_attachment=True
        ... )
        >>> print(f"Found {len(results['messages'])} invoices")
    """
    query_parts = []

    if from_email:
        query_parts.append(f'from:{from_email}')

    if to_email:
        query_parts.append(f'to:{to_email}')

    if subject:
        query_parts.append(f'subject:{subject}')

    if after_date:
        date_str = after_date.strftime('%Y/%m/%d')
        query_parts.append(f'after:{date_str}')

    if before_date:
        date_str = before_date.strftime('%Y/%m/%d')
        query_parts.append(f'before:{date_str}')

    if has_attachment:
        query_parts.append('has:attachment')

    if is_unread:
        query_parts.append('is:unread')

    if label:
        query_parts.append(f'label:{label}')

    query = ' '.join(query_parts)
    return list_emails(query=query, max_results=max_results)


def download_attachment(
    message_id: str,
    attachment_id: str,
    save_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Download an email attachment.

    Args:
        message_id: Gmail message ID containing the attachment.
        attachment_id: Attachment ID (from get_attachment_info).
        save_path: Optional file path to save attachment.
                   If not provided, returns raw bytes.

    Returns:
        Dictionary containing:
        - data: Attachment data as bytes
        - size: Size in bytes
        - saved_to: File path (if save_path was provided)

    Raises:
        ValueError: If attachment not found or authentication fails.

    Example:
        >>> # Download and save attachment
        >>> result = download_attachment(
        ...     'msg_id',
        ...     'attach_id',
        ...     save_path='/tmp/document.pdf'
        ... )
        >>> print(f"Saved to: {result['saved_to']}")
    """
    try:
        service = get_gmail_service()

        # Get the attachment
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()

        # Decode data
        data = attachment.get('data', '')
        decoded_data = base64.urlsafe_b64decode(data)

        result = {
            'data': decoded_data,
            'size': len(decoded_data),
        }

        # Save to file if path provided
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(decoded_data)
            result['saved_to'] = save_path

        return result

    except HttpError as error:
        if error.resp.status == 404:
            raise ValueError(f"Attachment not found: {attachment_id}")
        elif error.resp.status == 401:
            raise ValueError("Authentication failed. Re-run google_auth_setup.py")
        raise


# Convenience functions for common use cases

def get_unread_emails(max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Get unread emails.

    Args:
        max_results: Maximum number of emails to return.

    Returns:
        List of email dictionaries.

    Example:
        >>> unread = get_unread_emails(max_results=5)
        >>> for email in unread:
        ...     print(f"Unread from {email['from']}: {email['subject']}")
    """
    result = list_emails(query='is:unread', max_results=max_results)
    messages = result.get('messages', [])
    return [read_email(msg['id']) for msg in messages]


def get_emails_from_sender(sender: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Get emails from a specific sender.

    Args:
        sender: Sender email address.
        max_results: Maximum number of emails to return.

    Returns:
        List of email dictionaries.

    Example:
        >>> emails = get_emails_from_sender('boss@example.com', max_results=5)
        >>> for email in emails:
        ...     print(f"Subject: {email['subject']}")
    """
    result = search_emails(from_email=sender, max_results=max_results)
    messages = result.get('messages', [])
    return [read_email(msg['id']) for msg in messages]


def get_recent_emails(days: int = 7, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent emails from the last N days.

    Args:
        days: Number of days to look back.
        max_results: Maximum number of emails to return.

    Returns:
        List of email dictionaries.

    Example:
        >>> recent = get_recent_emails(days=3, max_results=10)
        >>> print(f"Found {len(recent)} emails in last 3 days")
    """
    from datetime import timedelta
    after_date = datetime.now() - timedelta(days=days)
    result = search_emails(after_date=after_date, max_results=max_results)
    messages = result.get('messages', [])
    return [read_email(msg['id']) for msg in messages]
