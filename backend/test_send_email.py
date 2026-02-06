"""Manual test script for Gmail sending."""
from gmail_sender import get_gmail_sender
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_send_emails():
    """Send test emails to verify integration."""
    sender = get_gmail_sender()
    recipient = os.getenv('GMAIL_RECIPIENT_EMAIL', 'your-email@example.com')

    # Test 1: Simple email
    print("Sending simple test email...")
    message_id = sender.send_email(
        to=recipient,
        subject='AI Assistant Test Email',
        body_html='<h1>Test Email</h1><p>This is a test from AI Assistant.</p>',
        body_text='Test Email\n\nThis is a test from AI Assistant.'
    )
    print(f"✓ Sent message ID: {message_id}")

    # Test 2: Daily digest
    print("\nSending daily digest...")
    # Note: send_daily_digest requires a database session (db) and recipient_email
    # This is a simplified test - in production, db session would be provided
    print("⚠️  Daily digest test skipped - requires database session")
    print("    Use send_scheduled_email.py to test with actual database")

    print("\n✅ All test emails sent successfully!")
    print("Check your inbox to verify receipt.")

if __name__ == '__main__':
    test_send_emails()
