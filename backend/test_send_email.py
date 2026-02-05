"""Manual test script for Gmail sending."""
from gmail_sender import get_gmail_sender
from datetime import datetime

def test_send_emails():
    """Send test emails to verify integration."""
    sender = get_gmail_sender()

    # Test 1: Simple email
    print("Sending simple test email...")
    message_id = sender.send_email(
        to='your-email@example.com',
        subject='AI Assistant Test Email',
        body_html='<h1>Test Email</h1><p>This is a test from AI Assistant.</p>',
        body_text='Test Email\n\nThis is a test from AI Assistant.'
    )
    print(f"✓ Sent message ID: {message_id}")

    # Test 2: Daily digest
    print("\nSending daily digest...")
    message_id = sender.send_daily_digest(datetime.now())
    print(f"✓ Sent digest message ID: {message_id}")

    print("\n✅ All test emails sent successfully!")
    print("Check your inbox to verify receipt.")

if __name__ == '__main__':
    test_send_emails()
