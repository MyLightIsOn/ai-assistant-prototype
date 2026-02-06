#!/usr/bin/env python3
"""
Scheduled email sender script.
This script is executed by scheduled tasks to send emails.
"""

import sys
from datetime import datetime
from gmail_sender import GmailSender

def main():
    # Get recipient from command line args
    recipient = sys.argv[1] if len(sys.argv) > 1 else 'thelawrencemoore@gmail.com'
    subject = sys.argv[2] if len(sys.argv) > 2 else '[AI Assistant] Scheduled Email'

    sender = GmailSender()

    body_text = f"""Hello!

This is a scheduled email from your AI Assistant.

✅ The scheduled task system is working correctly!
✅ Gmail integration is functional
✅ Task executed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This demonstrates that your AI assistant can:
- Run tasks on a schedule
- Send emails automatically
- Execute at specific times

Best regards,
Your AI Assistant
"""

    body_html = f"""
<html>
<body>
<h2>Hello!</h2>
<p>This is a scheduled email from your AI Assistant.</p>

<h3>✅ System Status</h3>
<ul>
  <li>The scheduled task system is working correctly!</li>
  <li>Gmail integration is functional</li>
  <li>Task executed at: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></li>
</ul>

<h3>Capabilities Demonstrated</h3>
<p>This demonstrates that your AI assistant can:</p>
<ul>
  <li>Run tasks on a schedule</li>
  <li>Send emails automatically</li>
  <li>Execute at specific times</li>
</ul>

<p>Best regards,<br><strong>Your AI Assistant</strong></p>
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
        print(f'✅ Email sent successfully to {recipient}')
        print(f'   Message ID: {message_id}')
        return 0
    except Exception as e:
        print(f'❌ Failed to send email: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
