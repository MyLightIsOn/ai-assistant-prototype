#!/usr/bin/env python3
"""
Send test email with subject "Hello World" and body "API Test".
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gmail_sender import GmailSender

def main():
    recipient = 'thelawrencemoore@gmail.com'
    subject = 'Hello World'

    sender = GmailSender()

    body_text = """API Test"""

    body_html = """
<html>
<body>
<p>API Test</p>
</body>
</html>
"""

    try:
        message_id = sender.send_email(
            to=recipient,
            subject=subject,
            body_html=body_html,
            body_text=body_text
        )
        print(f'✅ Test email sent successfully to {recipient}')
        print(f'   Subject: {subject}')
        print(f'   Body: API Test')
        print(f'   Message ID: {message_id}')
        return 0
    except Exception as e:
        print(f'❌ Failed to send email: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
