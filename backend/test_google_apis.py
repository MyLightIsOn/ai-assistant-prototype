#!/usr/bin/env python3
"""
Test script to verify Google API access.

Tests:
- Google Calendar API
- Google Drive API
- Gmail API
- Cloud Pub/Sub API
"""

import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

def get_credentials():
    """Get credentials from saved user credentials file."""
    credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google_user_credentials.json')

    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        print("   Run google_auth_setup.py first to authenticate")
        return None, None

    from google.oauth2.credentials import Credentials
    credentials = Credentials.from_authorized_user_file(credentials_file)
    project = os.getenv('GOOGLE_PROJECT_ID')

    return credentials, project

def test_calendar_api():
    """Test Google Calendar API access."""
    print("\n🗓️  Testing Google Calendar API...")
    credentials, _ = get_credentials()
    assert credentials is not None, "Failed to get credentials"

    service = build('calendar', 'v3', credentials=credentials)

    # List calendars
    calendar_list = service.calendarList().list().execute()
    calendars = calendar_list.get('items', [])

    print(f"   ✅ Calendar API working! Found {len(calendars)} calendar(s)")
    for cal in calendars:
        print(f"      - {cal.get('summary', 'Unnamed')} (ID: {cal.get('id')})")

def test_drive_api():
    """Test Google Drive API access."""
    print("\n📁 Testing Google Drive API...")
    credentials, _ = get_credentials()
    assert credentials is not None, "Failed to get credentials"

    service = build('drive', 'v3', credentials=credentials)

    # List files (limit to 5)
    results = service.files().list(
        pageSize=5,
        fields="files(id, name, mimeType)"
    ).execute()
    files = results.get('files', [])

    print(f"   ✅ Drive API working! Found {len(files)} recent file(s)")
    for file in files:
        print(f"      - {file.get('name')} ({file.get('mimeType')})")

def test_gmail_api():
    """Test Gmail API access."""
    print("\n📧 Testing Gmail API...")
    credentials, _ = get_credentials()
    assert credentials is not None, "Failed to get credentials"

    service = build('gmail', 'v1', credentials=credentials)

    # Get user profile
    profile = service.users().getProfile(userId='me').execute()
    email = profile.get('emailAddress')

    print(f"   ✅ Gmail API working! Connected as: {email}")
    print(f"      Messages in inbox: {profile.get('messagesTotal', 0)}")

def test_pubsub_api():
    """Test Cloud Pub/Sub API access."""
    print("\n📮 Testing Cloud Pub/Sub API...")
    from google.cloud import pubsub_v1

    project_id = os.getenv('GOOGLE_PROJECT_ID')
    assert project_id is not None, "GOOGLE_PROJECT_ID not set in .env"

    # Create publisher client
    publisher = pubsub_v1.PublisherClient()

    # List topics
    project_path = f"projects/{project_id}"
    topics = list(publisher.list_topics(request={"project": project_path}))

    print(f"   ✅ Pub/Sub API working! Found {len(topics)} topic(s)")
    for topic in topics[:5]:  # Show first 5
        print(f"      - {topic.name}")

def main():
    """Run all API tests."""
    print("=" * 60)
    print("🧪 Google Cloud API Access Test")
    print("=" * 60)

    # Check environment variables
    print("\n📋 Configuration:")
    print(f"   Project ID: {os.getenv('GOOGLE_PROJECT_ID')}")
    print(f"   AI Email: {os.getenv('GOOGLE_AI_EMAIL')}")
    print(f"   Credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")

    # Run tests
    results = {}
    for name, test_func in [
        ('Calendar API', test_calendar_api),
        ('Drive API', test_drive_api),
        ('Gmail API', test_gmail_api),
        ('Pub/Sub API', test_pubsub_api),
    ]:
        try:
            test_func()
            results[name] = True
        except (AssertionError, Exception) as e:
            print(f"   ❌ {name} error: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("=" * 60)

    for api, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {api}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Google Cloud APIs are ready to use.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    print("=" * 60)

if __name__ == '__main__':
    main()
