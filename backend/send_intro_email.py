#!/usr/bin/env python3
"""
Send introductory email from AI Assistant.
"""

import sys
import os
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gmail_sender import GmailSender

def main():
    recipient = 'thelawrencemoore@gmail.com'
    subject = 'Introduction from your AI Assistant'

    sender = GmailSender()

    body_text = """Hi, I'm the new AI Assistant. Let's set up a introductory meeting. Is that ok?"""

    body_html = """
<html>
<body>
<p>Hi, I'm the new AI Assistant. Let's set up a introductory meeting. Is that ok?</p>
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
        print(f'✅ Introductory email sent successfully to {recipient}')
        print(f'   Message ID: {message_id}')
        return 0
    except Exception as e:
        print(f'❌ Failed to send email: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
