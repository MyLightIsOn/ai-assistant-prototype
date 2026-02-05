# Gmail Client Usage Guide

This guide provides examples and integration patterns for the Gmail client module.

## Overview

The Gmail client provides manual/on-demand email reading functionality. It does **NOT** implement automatic monitoring - all operations must be explicitly triggered.

## Features

- Read individual emails with full details
- List emails with Gmail search queries
- Search emails using common criteria
- Download attachments
- Parse email headers and bodies (plain text + HTML)
- Convenience functions for common use cases

## Prerequisites

1. **Google OAuth Setup**: Run `google_auth_setup.py` to authenticate
2. **Gmail API Enabled**: Ensure Gmail API is enabled in Google Cloud Console
3. **Required Scopes**:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`

## Basic Usage

### Reading a Specific Email

```python
from gmail_client import read_email

# Read email by message ID
email = read_email('18f2c3a1b2d4e5f6')

print(f"From: {email['from']}")
print(f"Subject: {email['subject']}")
print(f"Date: {email['date']}")
print(f"Body: {email['body']}")

# Check for attachments
if email['attachments']:
    print(f"Attachments: {len(email['attachments'])}")
    for att in email['attachments']:
        print(f"  - {att['filename']} ({att['size']} bytes)")
```

### Listing Emails

```python
from gmail_client import list_emails

# List recent emails (default: 10)
result = list_emails()
for msg in result['messages']:
    email = read_email(msg['id'])
    print(f"{email['subject']} - {email['from']}")

# List with Gmail query
result = list_emails(query='is:unread', max_results=5)

# List with pagination
result = list_emails(query='from:boss@example.com', max_results=50, include_all_pages=True)
```

### Searching Emails

```python
from gmail_client import search_emails
from datetime import datetime, timedelta

# Search by sender
result = search_emails(from_email='billing@example.com')

# Search by subject
result = search_emails(subject='Invoice')

# Search by date
last_week = datetime.now() - timedelta(days=7)
result = search_emails(after_date=last_week)

# Combined search
result = search_emails(
    from_email='billing@example.com',
    subject='Invoice',
    after_date=last_week,
    has_attachment=True,
    is_unread=True,
    max_results=20
)

# Process results
for msg in result['messages']:
    email = read_email(msg['id'])
    print(f"Invoice from {email['date']}")
```

### Downloading Attachments

```python
from gmail_client import read_email, download_attachment

# First, get email and find attachments
email = read_email('msg_id')

for att in email['attachments']:
    print(f"Downloading: {att['filename']}")

    # Download to file
    result = download_attachment(
        message_id=email['id'],
        attachment_id=att['attachment_id'],
        save_path=f"/tmp/{att['filename']}"
    )

    print(f"Saved to: {result['saved_to']}")
    print(f"Size: {result['size']} bytes")
```

### Convenience Functions

```python
from gmail_client import (
    get_unread_emails,
    get_emails_from_sender,
    get_recent_emails
)

# Get unread emails
unread = get_unread_emails(max_results=10)
for email in unread:
    print(f"Unread: {email['subject']}")

# Get emails from specific sender
emails = get_emails_from_sender('boss@example.com', max_results=5)

# Get recent emails (last 7 days)
recent = get_recent_emails(days=7, max_results=20)
```

## Gmail Query Syntax

The `list_emails()` function accepts Gmail's powerful query syntax:

```python
# Common queries
list_emails(query='is:unread')                    # Unread emails
list_emails(query='is:starred')                   # Starred emails
list_emails(query='from:sender@example.com')      # From specific sender
list_emails(query='to:me')                        # Sent to you
list_emails(query='subject:Invoice')              # Subject contains "Invoice"
list_emails(query='has:attachment')               # Has attachments
list_emails(query='label:IMPORTANT')              # Specific label
list_emails(query='after:2024/01/01')             # After date
list_emails(query='before:2024/12/31')            # Before date

# Combined queries
list_emails(query='from:billing@example.com has:attachment is:unread')
list_emails(query='subject:Invoice after:2024/01/01')
```

## Email Data Structure

The `read_email()` function returns a dictionary with:

```python
{
    'id': 'msg_18f2c3a1b2d4e5f6',
    'thread_id': 'thread_123',
    'labels': ['INBOX', 'UNREAD'],
    'snippet': 'Email preview text...',
    'subject': 'Email Subject',
    'from': 'sender@example.com',
    'to': 'recipient@example.com',
    'cc': 'cc@example.com',         # Optional
    'date': 'Mon, 01 Jan 2024 00:00:00 +0000',
    'message_id': '<abc123@example.com>',
    'body': 'Plain text body...',
    'html_body': '<html>...</html>',  # Optional, if HTML version exists
    'attachments': [
        {
            'filename': 'document.pdf',
            'mime_type': 'application/pdf',
            'attachment_id': 'attach_123',
            'size': 5000
        }
    ]
}
```

## Error Handling

```python
from gmail_client import read_email

try:
    email = read_email('msg_id')
except ValueError as e:
    if "not found" in str(e):
        print("Email does not exist")
    elif "Authentication failed" in str(e):
        print("Need to re-authenticate. Run google_auth_setup.py")
    elif "Rate limit exceeded" in str(e):
        print("Too many requests. Wait and try again")
    else:
        print(f"Error: {e}")
except ConnectionError:
    print("Network error. Check internet connection")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Integration with Chat Commands

Here are example integration patterns for chat-based AI commands:

### Pattern 1: Check for Specific Email

```python
def handle_check_email_command(sender: str = None, subject: str = None):
    """Handle 'check email' command from chat."""
    from gmail_client import search_emails, read_email

    try:
        # Search for emails
        results = search_emails(
            from_email=sender,
            subject=subject,
            is_unread=True,
            max_results=5
        )

        if not results['messages']:
            return "No matching emails found"

        # Format response
        response = f"Found {len(results['messages'])} email(s):\n\n"
        for msg in results['messages']:
            email = read_email(msg['id'])
            response += f"From: {email['from']}\n"
            response += f"Subject: {email['subject']}\n"
            response += f"Preview: {email['snippet']}\n"
            response += "-" * 50 + "\n"

        return response

    except Exception as e:
        return f"Error checking email: {e}"
```

### Pattern 2: Get Email Summary

```python
def handle_email_summary_command(days: int = 1):
    """Handle 'email summary' command from chat."""
    from gmail_client import get_recent_emails
    from datetime import datetime, timedelta

    try:
        emails = get_recent_emails(days=days, max_results=50)

        # Group by sender
        by_sender = {}
        for email in emails:
            sender = email['from']
            if sender not in by_sender:
                by_sender[sender] = []
            by_sender[sender].append(email)

        # Format summary
        response = f"Email Summary (Last {days} day(s)):\n\n"
        response += f"Total: {len(emails)} email(s)\n"
        response += f"From {len(by_sender)} sender(s)\n\n"

        for sender, sender_emails in by_sender.items():
            response += f"{sender}: {len(sender_emails)} email(s)\n"
            for email in sender_emails[:3]:  # Show first 3
                response += f"  - {email['subject']}\n"

        return response

    except Exception as e:
        return f"Error generating summary: {e}"
```

### Pattern 3: Download Invoice Attachments

```python
def handle_download_invoices_command(output_dir: str = "/tmp/invoices"):
    """Handle 'download invoices' command from chat."""
    from gmail_client import search_emails, read_email, download_attachment
    import os

    try:
        # Search for invoice emails
        results = search_emails(
            subject='Invoice',
            has_attachment=True,
            max_results=10
        )

        os.makedirs(output_dir, exist_ok=True)
        downloaded = []

        for msg in results['messages']:
            email = read_email(msg['id'])

            for att in email['attachments']:
                # Only download PDFs
                if att['mime_type'] == 'application/pdf':
                    filename = att['filename']
                    output_path = os.path.join(output_dir, filename)

                    download_attachment(
                        message_id=email['id'],
                        attachment_id=att['attachment_id'],
                        save_path=output_path
                    )

                    downloaded.append(filename)

        if downloaded:
            response = f"Downloaded {len(downloaded)} invoice(s):\n"
            for filename in downloaded:
                response += f"  - {filename}\n"
            response += f"\nSaved to: {output_dir}"
            return response
        else:
            return "No invoice attachments found"

    except Exception as e:
        return f"Error downloading invoices: {e}"
```

### Pattern 4: Unread Email Notification

```python
def handle_unread_check_command():
    """Handle 'check unread' command from chat."""
    from gmail_client import get_unread_emails

    try:
        unread = get_unread_emails(max_results=10)

        if not unread:
            return "No unread emails"

        # Format notification
        response = f"You have {len(unread)} unread email(s):\n\n"

        for email in unread:
            response += f"From: {email['from']}\n"
            response += f"Subject: {email['subject']}\n"
            response += f"Preview: {email['snippet'][:100]}...\n"

            if email['attachments']:
                response += f"Attachments: {len(email['attachments'])}\n"

            response += "-" * 50 + "\n"

        return response

    except Exception as e:
        return f"Error checking unread emails: {e}"
```

## Integration with Task Scheduler

Example of scheduling periodic email checks:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from gmail_client import get_unread_emails
from ntfy_client import send_notification

def check_important_emails():
    """Scheduled task to check for important emails."""
    try:
        # Search for important unread emails
        from gmail_client import search_emails

        results = search_emails(
            is_unread=True,
            label='IMPORTANT',
            max_results=5
        )

        if results['messages']:
            # Send notification
            message = f"You have {len(results['messages'])} important unread email(s)"
            send_notification(
                title="Important Emails",
                message=message,
                priority=4
            )
    except Exception as e:
        print(f"Error checking emails: {e}")

# Schedule to run every hour
scheduler = BackgroundScheduler()
scheduler.add_job(
    check_important_emails,
    'interval',
    hours=1,
    id='check_important_emails'
)
scheduler.start()
```

## Best Practices

1. **Authentication**: Always check credentials before operations
   ```python
   from gmail_client import get_gmail_service

   try:
       service = get_gmail_service()
   except FileNotFoundError:
       print("Run google_auth_setup.py first")
   ```

2. **Rate Limiting**: Implement backoff for bulk operations
   ```python
   import time

   for msg in messages:
       email = read_email(msg['id'])
       # Process email
       time.sleep(0.1)  # Avoid rate limits
   ```

3. **Error Recovery**: Always handle Gmail API errors
   ```python
   from googleapiclient.errors import HttpError

   try:
       email = read_email('msg_id')
   except HttpError as e:
       if e.resp.status == 429:
           # Rate limited - wait and retry
           time.sleep(60)
       elif e.resp.status == 404:
           # Email not found - skip
           pass
   ```

4. **Efficient Queries**: Use Gmail queries instead of filtering in code
   ```python
   # Good: Filter in query
   results = list_emails(query='from:sender@example.com after:2024/01/01')

   # Bad: Fetch all then filter
   results = list_emails(max_results=1000)
   filtered = [m for m in results if ...]  # Inefficient
   ```

5. **Attachment Safety**: Verify attachment types before downloading
   ```python
   ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png']

   for att in email['attachments']:
       if att['mime_type'] in ALLOWED_TYPES:
           download_attachment(...)
   ```

## Testing

The module includes comprehensive tests. Run them with:

```bash
cd backend
source venv/bin/activate
pytest tests/test_gmail_client.py -v
```

Tests cover:
- Reading emails (plain text, HTML, multipart)
- Listing and searching
- Attachment handling
- Error conditions (404, 401, 429, network errors)
- Parsing utilities
- Credential management

## Limitations

1. **Manual Only**: No automatic monitoring or webhooks
2. **Read-Only Focus**: While send scope is included, sending is not implemented
3. **Rate Limits**: Subject to Gmail API quotas (see Google Cloud Console)
4. **Authentication**: Requires periodic re-authentication (refresh token expires)

## Troubleshooting

### "Credentials file not found"
Run `google_auth_setup.py` to authenticate:
```bash
python google_auth_setup.py
```

### "Authentication failed"
Re-run authentication setup:
```bash
python google_auth_setup.py
```

### "Rate limit exceeded"
Wait and retry. Implement exponential backoff:
```python
import time

for attempt in range(3):
    try:
        result = list_emails(...)
        break
    except ValueError as e:
        if "Rate limit" in str(e) and attempt < 2:
            wait = (2 ** attempt) * 30  # 30s, 60s, 120s
            time.sleep(wait)
        else:
            raise
```

### Empty body text
Some emails may have complex MIME structures. Check for HTML body:
```python
email = read_email('msg_id')
if not email['body'] and email.get('html_body'):
    # Use HTML body instead
    body = email['html_body']
```

## Security Considerations

1. **Credentials**: Store `google_user_credentials.json` securely (already in .gitignore)
2. **Attachment Downloads**: Validate file paths to prevent directory traversal
3. **Email Content**: Sanitize before displaying (especially HTML bodies)
4. **Access Control**: Limit who can trigger email operations
5. **Logging**: Log all email access for audit trail

## Future Enhancements

Potential improvements (NOT in current scope):

- Send email functionality
- Mark emails as read/unread
- Add/remove labels
- Create filters
- Batch operations
- Email caching
- Full-text search in email bodies
- Thread management

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Gmail Search Operators](https://support.google.com/mail/answer/7190)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
