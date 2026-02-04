#!/usr/bin/env python3
"""
Google OAuth 2.0 Authentication Setup

This script performs the OAuth flow to get user credentials
and saves them for use by the AI Assistant backend.

Run this once to authorize the application.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Define the scopes we need
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/pubsub',
]

# File paths
CLIENT_SECRET_FILE = 'google_oauth_client.json'
CREDENTIALS_FILE = 'google_user_credentials.json'

def authenticate():
    """
    Perform OAuth 2.0 flow to get user credentials.

    This will:
    1. Open a browser for you to authorize the app
    2. Save the credentials (including refresh token) to a file
    3. Allow the backend to access Google APIs on your behalf
    """
    creds = None

    # Check if we already have credentials
    if os.path.exists(CREDENTIALS_FILE):
        print(f"📄 Found existing credentials: {CREDENTIALS_FILE}")
        try:
            creds = Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)
        except Exception as e:
            print(f"   ⚠️  Could not load credentials: {e}")
            creds = None

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired credentials...")
            try:
                creds.refresh(Request())
                print("   ✅ Credentials refreshed successfully")
            except Exception as e:
                print(f"   ❌ Could not refresh credentials: {e}")
                print("   🔑 Starting new OAuth flow...")
                creds = None

        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"❌ Client secret file not found: {CLIENT_SECRET_FILE}")
                print("   Please download the OAuth client credentials from Google Cloud Console")
                return None

            print("🔑 Starting OAuth 2.0 flow...")
            print("   A browser window will open for you to authorize the application")

            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES
            )

            # Run local server for OAuth callback
            creds = flow.run_local_server(port=0)  # Use port 0 for automatic port selection
            print("   ✅ Authorization successful!")

        # Save the credentials for future use
        print(f"💾 Saving credentials to: {CREDENTIALS_FILE}")
        with open(CREDENTIALS_FILE, 'w') as token:
            token.write(creds.to_json())
        print("   ✅ Credentials saved successfully")
    else:
        print("✅ Valid credentials already exist")

    return creds

def verify_credentials(creds):
    """Verify credentials work by getting user info."""
    from googleapiclient.discovery import build

    try:
        # Test Gmail API
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')
        print(f"\n✅ Authentication verified!")
        print(f"   Authenticated as: {email}")
        print(f"   Messages total: {profile.get('messagesTotal', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        return False

def main():
    """Main authentication setup."""
    print("=" * 60)
    print("🔐 Google OAuth 2.0 Authentication Setup")
    print("=" * 60)
    print("\nThis will authorize the AI Assistant to access:")
    print("  📅 Google Calendar")
    print("  📁 Google Drive")
    print("  📧 Gmail")
    print("  📮 Cloud Pub/Sub")
    print("\nYour credentials will be saved locally and encrypted.")
    print("=" * 60)

    # Perform authentication
    creds = authenticate()

    if creds:
        # Verify it works
        verify_credentials(creds)

        print("\n" + "=" * 60)
        print("🎉 Setup Complete!")
        print("=" * 60)
        print(f"✅ Credentials saved to: {CREDENTIALS_FILE}")
        print("✅ The backend can now access Google APIs")
        print("\nNext steps:")
        print("  1. Update .env to use these credentials")
        print("  2. Run test_google_apis.py to verify all APIs work")
        print("=" * 60)
        return True
    else:
        print("\n❌ Authentication failed. Please try again.")
        return False

if __name__ == '__main__':
    main()
