# Google Workspace Setup Guide

This guide walks through setting up Google Workspace services for the AI assistant.

## Overview

The AI will have its own Gmail account and Google Cloud project to access:
- **Gmail** - Send detailed reports and notifications
- **Google Calendar** - Task visualization and manual scheduling
- **Google Drive** - Long-term log archival and file storage
- **Google Docs/Sheets** - Formatted reports
- **Cloud Pub/Sub** - Event bus for Calendar webhooks

## Prerequisites

- Google account (for creating AI's account and Cloud project)
- Payment method for Google Cloud (free tier sufficient, but card required)
- Access to Google Workspace or standard Gmail

## Step 1: Create AI Gmail Account

### 1.1 Create New Gmail Account

1. Go to https://accounts.google.com/signup
2. Create account: **your-ai-assistant@gmail.com**
3. Use strong password (store securely)
4. Complete phone verification
5. Accept terms of service

### 1.2 Configure Account Settings

1. **Profile**: Add profile picture (optional, makes AI recognizable)
2. **Recovery email**: Add your personal email
3. **Security**: Enable 2FA (recommended)

## Step 2: Create Google Cloud Project

### 2.1 Setup Project

1. Go to https://console.cloud.google.com
2. Sign in with AI's Gmail account
3. Create new project: **"AI Assistant"**
4. Note the Project ID (e.g., `ai-assistant-123456`)

### 2.2 Enable Billing

1. Go to **Billing** in Cloud Console
2. Link a payment method
3. Free tier is sufficient for this use case:
   - Calendar API: Free
   - Drive API: Free
   - Gmail API: Free
   - Pub/Sub: Free tier (10 GB/month)

### 2.3 Enable APIs

Enable these APIs in **APIs & Services > Library**:

- [x] Google Calendar API
- [x] Google Drive API
- [x] Gmail API
- [x] Cloud Pub/Sub API

## Step 3: Create Service Account Credentials

### 3.1 Create Service Account

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > Service Account**
3. Name: `ai-assistant-service`
4. Description: "AI Assistant service account"
5. Click **Create and Continue**
6. Grant role: **Editor** (or specific roles for each API)
7. Click **Done**

### 3.2 Download Credentials

1. Click on the service account you just created
2. Go to **Keys** tab
3. Click **Add Key > Create new key**
4. Choose **JSON** format
5. Download the key file
6. **IMPORTANT**: Store securely, never commit to git!
7. Rename to `google-credentials.json`
8. Place in backend directory (add to .gitignore)

### 3.3 Grant Permissions

The service account needs access to AI's resources:

**Calendar:**
1. Go to https://calendar.google.com (signed in as AI)
2. Settings > Settings for my calendars > Share with specific people
3. Add service account email (from credentials JSON)
4. Permission: **Make changes to events**

**Drive:**
1. Create "AI Assistant Drive" folder
2. Share with service account email
3. Permission: **Editor**

## Step 4: Setup Google Calendar

### 4.1 Create AI Calendar

1. Go to https://calendar.google.com (signed in as AI)
2. Click **+** next to "Other calendars"
3. Create new calendar: **"AI Tasks"**
4. Description: "Scheduled tasks and executions"
5. Time zone: Your local timezone

### 4.2 Share Calendar with User

1. Settings > Settings for my calendars > **AI Tasks**
2. Share with specific people
3. Add your personal Gmail
4. Permission: **Make changes to events** (so you can edit task timing)

### 4.3 Configure Calendar Colors

Calendar will use these colors for priority levels:
- **Blue** (Peacock): Low priority
- **Green** (Sage): Default priority
- **Orange** (Tangerine): High priority
- **Red** (Tomato): Urgent priority

## Step 5: Setup Google Drive

### 5.1 Create Folder Structure

In AI's Google Drive, create:

```
AI Assistant/
├── logs/
│   ├── 2026/
│   │   └── 02/
├── reports/
│   ├── weekly-summaries/
│   └── task-reports/
├── research/
└── artifacts/
```

### 5.2 Share Root Folder

1. Right-click "AI Assistant" folder
2. Share > Add your personal Gmail
3. Permission: **Editor**
4. Uncheck "Notify people"

## Step 6: Setup Cloud Pub/Sub

### 6.1 Create Topic

1. Go to **Pub/Sub > Topics** in Cloud Console
2. Click **Create Topic**
3. Topic ID: `calendar-notifications`
4. Leave defaults
5. Click **Create**

### 6.2 Create Subscription

1. Click on the topic you created
2. Click **Create Subscription**
3. Subscription ID: `calendar-notifications-sub`
4. Delivery type: **Push**
5. Endpoint URL: `https://your-tailscale-hostname:8000/api/google/calendar/webhook`
   - Replace with your actual backend URL
   - Must be HTTPS (Pub/Sub requirement)
6. Click **Create**

### 6.3 Setup Calendar Watch

This will be done programmatically by the Python backend on startup:

```python
from googleapiclient.discovery import build

service = build('calendar', 'v3', credentials=creds)

watch_request = {
    'id': 'ai-assistant-calendar-watch',
    'type': 'web_hook',
    'address': 'https://pubsub.googleapis.com/projects/YOUR_PROJECT_ID/topics/calendar-notifications'
}

service.events().watch(calendarId='primary', body=watch_request).execute()
```

## Step 7: Configure Backend

### 7.1 Environment Variables

Add to `backend/.env`:

```bash
# Google Workspace
GOOGLE_CREDENTIALS_PATH="./google-credentials.json"
GOOGLE_PROJECT_ID="ai-assistant-123456"
GOOGLE_AI_EMAIL="your-ai-assistant@gmail.com"
GOOGLE_CALENDAR_ID="primary"
GOOGLE_DRIVE_FOLDER_ID="<folder-id-from-drive-url>"
GOOGLE_PUBSUB_TOPIC="calendar-notifications"
GOOGLE_PUBSUB_SUBSCRIPTION="calendar-notifications-sub"
```

### 7.2 Install Python Dependencies

Add to `backend/requirements.txt`:

```
google-auth>=2.27.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
google-api-python-client>=2.116.0
google-cloud-pubsub>=2.19.0
```

Install:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

## Step 8: Testing

### 8.1 Test Calendar Access

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    'google-credentials.json',
    scopes=['https://www.googleapis.com/auth/calendar']
)

service = build('calendar', 'v3', credentials=creds)
calendar_list = service.calendarList().list().execute()
print(calendar_list)
```

### 8.2 Test Drive Access

```python
service = build('drive', 'v3', credentials=creds)
results = service.files().list(pageSize=10).execute()
print(results)
```

### 8.3 Test Gmail Sending

```python
from email.mime.text import MIMEText
import base64

service = build('gmail', 'v1', credentials=creds)

message = MIMEText('Test email from AI assistant')
message['to'] = 'your-personal-email@gmail.com'
message['subject'] = 'AI Assistant Test'

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
service.users().messages().send(userId='me', body={'raw': raw}).execute()
```

### 8.4 Test Gmail Reading

```python
# List recent emails
service = build('gmail', 'v1', credentials=creds)
results = service.users().messages().list(userId='me', maxResults=10).execute()
messages = results.get('messages', [])

# Read first email
if messages:
    msg = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
    print(f"Subject: {msg['snippet']}")

    # Get email body
    payload = msg['payload']
    headers = payload.get('headers', [])
    for header in headers:
        if header['name'] == 'Subject':
            print(f"Full Subject: {header['value']}")
```

## Step 9: Gmail Reading Setup (Manual Only)

**Important:** AI will NOT automatically monitor inbox. It only reads emails when explicitly instructed by the user.

### 9.1 User Setup

1. **Add AI's Gmail to your phone:**
   - Settings > Accounts > Add Account
   - Sign in with AI's Gmail credentials
   - Enable notifications
2. **Workflow:**
   - Email arrives in AI's inbox
   - You see notification on your phone
   - You decide if AI should read/process it
   - You tell AI: "Read the email from X about Y"
   - AI searches, reads, and processes on command

### 9.2 Gmail API Scopes

The service account needs these scopes for manual reading:

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Read emails
    'https://www.googleapis.com/auth/gmail.send',      # Send emails
    'https://www.googleapis.com/auth/gmail.modify'     # Mark as read, apply labels
]
```

Or use full access (recommended since it's AI's dedicated account):
```python
SCOPES = ['https://mail.google.com/']
```

**No Pub/Sub setup needed** - AI reads emails only when you tell it to.

## Step 10: Calendar Pub/Sub Setup

### 10.1 Create Calendar Pub/Sub Topic

(Note: If you already created Pub/Sub topic in Step 6, skip to 10.2)

1. Go to **Pub/Sub > Topics** in Cloud Console
2. Click **Create Topic**
3. Topic ID: `calendar-notifications`
4. Click **Create**

### 10.2 Create Calendar Subscription

1. Click on `calendar-notifications` topic
2. Click **Create Subscription**
3. Subscription ID: `calendar-notifications-sub`
4. Delivery type: **Push**
5. Endpoint URL: `https://your-tailscale-hostname:8000/api/google/calendar/webhook`
6. Click **Create**

### 10.3 Pub/Sub Webhook Verification

Google Pub/Sub will send verification requests. Your webhook endpoints must:

1. Verify message signature
2. Return 200 OK quickly
3. Process message asynchronously

Example verification:
```python
from google.cloud import pubsub_v1

def verify_pubsub_message(request):
    # Verify the message token
    if 'X-Goog-Resource-State' in request.headers:
        return True
    return False
```

## Security Considerations

### Credentials Security

- **NEVER** commit `google-credentials.json` to git
- Store credentials in backend directory (gitignored)
- Use environment variables for sensitive config
- Rotate credentials periodically

### Access Controls

- Service account has minimal necessary permissions
- User has view/edit access to shared resources only
- Calendar and Drive are not public
- Pub/Sub requires authenticated requests

### Network Security

- Pub/Sub webhook endpoint requires HTTPS
- Use Tailscale for secure access to backend
- Pub/Sub messages include verification tokens

## Troubleshooting

### "Insufficient Permission" Error

- Check service account has correct roles in Cloud Console
- Verify Calendar/Drive sharing with service account email
- Ensure APIs are enabled

### Pub/Sub Not Receiving Messages

- Check webhook URL is HTTPS and accessible
- Verify subscription is in "Active" state
- Check Cloud Console > Pub/Sub > Metrics for delivery attempts
- Review backend logs for webhook errors

### Calendar Events Not Syncing

- Verify Calendar watch is active (renew every week)
- Check Pub/Sub subscription is receiving messages
- Review backend logs for sync errors

## Cost Estimate

Free tier covers typical usage:
- Calendar API: Free (unlimited)
- Drive API: Free (15 GB storage included)
- Gmail API: Free (read and send, within daily limits)
- Pub/Sub: Free tier (10 GB messages/month)

**Estimated monthly cost: $0** (within free tier limits)

## Next Steps

Once setup is complete:
1. Run backend tests to verify all integrations
2. Create first task and verify Calendar sync
3. Test Pub/Sub webhook by creating Calendar event
4. Verify Drive archival by running a task
5. Test email reports (sending)
6. Test email monitoring by forwarding an email to AI
7. Verify Gmail push notifications working

## Resources

- [Google Calendar API Docs](https://developers.google.com/calendar/api)
- [Google Drive API Docs](https://developers.google.com/drive/api)
- [Gmail API Docs](https://developers.google.com/gmail/api)
- [Cloud Pub/Sub Docs](https://cloud.google.com/pubsub/docs)
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
