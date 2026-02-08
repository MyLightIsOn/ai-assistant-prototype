#!/usr/bin/env python3
"""
Send scheduler test email.
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gmail_sender import GmailSender

def main():
    recipient = 'thelawrencemoore@gmail.com'
    subject = 'Scheduler Test'

    sender = GmailSender()

    body_text = "6PM Execution - Automated scheduler is working!"

    body_html = """
<html>
<body>
<p>6PM Execution - Automated scheduler is working!</p>
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
        print(f'✅ Scheduler test email sent successfully to {recipient}')
        print(f'   Message ID: {message_id}')
        return 0
    except Exception as e:
        print(f'❌ Failed to send email: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
