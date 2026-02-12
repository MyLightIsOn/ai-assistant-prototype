# AI Assistant Chat - User Guide

A comprehensive guide for using the AI Assistant chat feature from any device on your Tailscale network.

---

## Table of Contents

1. [Overview](#overview)
2. [Accessing from Different Devices](#accessing-from-different-devices)
3. [Using the Chat Interface](#using-the-chat-interface)
4. [Managing Tasks with Natural Language](#managing-tasks-with-natural-language)
5. [Tips & Best Practices](#tips--best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The AI Assistant chat feature provides a hybrid interface that combines:
- **Natural conversation** - Chat with Claude AI like you would with a colleague
- **Task management** - Create, update, and manage scheduled tasks using natural language
- **Real-time responses** - See AI responses stream in as they're generated
- **Persistent history** - All conversations are saved and accessible across sessions

### Key Features

✅ **Markdown support** - Formatted text, code blocks with syntax highlighting, lists, and links
✅ **WebSocket streaming** - Real-time responses with typing indicators
✅ **Task management** - AI has access to task management via REST API
✅ **Message persistence** - Chat history preserved across page refreshes
✅ **Connection resilience** - Automatic reconnection if network drops

---

## Accessing from Different Devices

### Prerequisites

1. **Tailscale VPN** - All devices must be on the same Tailscale network
2. **Server running** - The AI Assistant backend and frontend must be running on the Mac Mini

### Step 1: Get the Tailscale Hostname

On your Mac Mini (server), find your Tailscale hostname:

```bash
tailscale status
```

Look for your Mac Mini's Tailscale hostname (e.g., `mac-mini.tailnet-name.ts.net`)

### Step 2: Access from Different Devices

#### From a Laptop/Desktop

1. Ensure Tailscale is running and connected
2. Open your browser (Chrome, Firefox, Safari, Edge)
3. Navigate to: `http://[mac-mini-hostname]:3000/chat`
   - Example: `http://mac-mini.tailnet-name.ts.net:3000/chat`
4. Log in with your credentials

#### From a Mobile Device (iPhone/Android)

1. Install Tailscale app from App Store / Play Store
2. Connect to your Tailscale network
3. Open your mobile browser
4. Navigate to: `http://[mac-mini-hostname]:3000/chat`
5. Log in with your credentials

**Tip:** Add the chat page to your home screen for quick access:
- **iOS Safari:** Tap Share → Add to Home Screen
- **Android Chrome:** Tap Menu → Add to Home screen

#### From a Tablet (iPad/Android Tablet)

Same process as mobile devices. The responsive design adapts to tablet screens.

### Step 3: Verify Connection

You should see:
- ✅ Green "Connected" indicator at the top of the chat
- ✅ Empty state message: "No messages yet. Start a conversation!"
- ✅ Chat input field at the bottom

If you see a red "Connection error" indicator, see [Troubleshooting](#troubleshooting).

---

## Using the Chat Interface

### Sending Messages

1. **Type your message** in the input field at the bottom
2. **Press Enter** to send (or click the send button)
   - Hold **Shift+Enter** to add a new line without sending
3. Your message appears immediately
4. AI response streams in with a typing indicator

### Understanding the UI

#### Connection Status Badge
- 🟢 **Connected** - WebSocket connected, ready to chat
- 🟡 **Connecting...** - Attempting to connect (pulsing indicator)
- 🔴 **Connection error** - Unable to connect to backend
- ⚪ **Disconnected** - Not connected (will auto-retry)

#### Message Indicators
- **"AI is streaming..."** - AI is actively generating a response
- **Bouncing dots** - Content is being streamed in real-time
- **Timestamp** - Shows relative time (e.g., "2 minutes ago")

#### Message Types
- **User messages** - Right-aligned, blue background
- **Assistant messages** - Left-aligned, gray background
- **Error messages** - Red-tinted background with error details

### Message Formatting

The AI can format responses with rich markdown:

**Bold text**
*Italic text*
`inline code`

```python
# Code blocks with syntax highlighting
def hello():
    print("Hello, world!")
```

- Bullet lists
- Nested lists
  - Sub-items

1. Numbered lists
2. Sequential items

[Links](https://example.com)

> Blockquotes

### Example Conversations

#### Simple Question
```
You: What's the weather like today?
AI: I don't have access to real-time weather data, but I can help you
    create a task to check the weather daily if you'd like!
```

#### Code Help
```
You: How do I read a file in Python?
AI: Here's how to read a file in Python:

    ```python
    # Method 1: Read entire file
    with open('file.txt', 'r') as f:
        content = f.read()

    # Method 2: Read line by line
    with open('file.txt', 'r') as f:
        for line in f:
            print(line.strip())
    ```

    The `with` statement ensures the file is properly closed.
```

---

## Managing Tasks with Natural Language

The AI has access to task management via the backend REST API. You can create, update, list, and delete tasks using natural language. The AI uses its Bash tool with curl to interact with the task API.

### Creating Tasks

Simply describe what you want in natural language:

```
You: Create a task to backup my database every night at 2am
AI: I'll create that task for you.

    ✅ Task created successfully!

    **Task Details:**
    - Name: Database Backup
    - Schedule: 0 2 * * * (Every day at 2:00 AM)
    - Command: [backup script]
    - Status: Enabled

    The task will run automatically at 2 AM every night.
```

**More Examples:**

```
"Remind me to review logs every Monday at 9am"
"Create a weekly task to update dependencies on Fridays"
"Set up a daily check at noon to verify the server is running"
"Schedule a monthly report on the first day of each month"
```

### Viewing Tasks

Ask to see your tasks:

```
You: Show me all my tasks
AI: Here are your current tasks:

    ✅ **Database Backup** (Enabled)
    - Schedule: 0 2 * * * (Every day at 2:00 AM)
    - Priority: High

    ✅ **Log Review** (Enabled)
    - Schedule: 0 9 * * 1 (Mondays at 9:00 AM)
    - Priority: Medium

    ✗ **Test Task** (Disabled)
    - Schedule: 0 12 * * *
    - Priority: Low
```

**Filtering:**

```
"Show me only enabled tasks"
"List all disabled tasks"
"What tasks do I have?"
```

### Updating Tasks

Modify tasks using natural language:

```
You: Change the database backup to run at 3am instead
AI: I've updated the task schedule.

    ✅ Task "Database Backup" updated successfully!

    **Changes:**
    - Old schedule: 0 2 * * *
    - New schedule: 0 3 * * *

    The backup will now run at 3:00 AM daily.
```

**More Examples:**

```
"Disable the log review task"
"Enable the test task"
"Change the priority of database backup to high"
"Update the weekly report to run on Saturdays"
```

### Deleting Tasks

Remove tasks you no longer need:

```
You: Delete the test task
AI: Are you sure you want to delete "Test Task"? This cannot be undone.

You: Yes, delete it
AI: ✅ Task "Test Task" has been deleted successfully.
```

### Checking Task History

View execution history:

```
You: Show me the execution history for database backup
AI: Here's the recent execution history for "Database Backup":

    ✅ Feb 8, 2026 at 2:00 AM - Success (Duration: 2m 34s)
    ✅ Feb 7, 2026 at 2:00 AM - Success (Duration: 2m 41s)
    ❌ Feb 6, 2026 at 2:00 AM - Failed (Error: Connection timeout)
    ✅ Feb 5, 2026 at 2:00 AM - Success (Duration: 2m 28s)

    Success rate: 75% (3/4 executions)
```

### Running Tasks Manually

Trigger a task immediately:

```
You: Run the database backup task now
AI: I've triggered the database backup task.

    ⏳ Execution started...

    (The task will run in the background. Check the Activity page
     for real-time status updates.)
```

---

## Tips & Best Practices

### 💡 Communication Tips

1. **Be specific** - "Create a task to backup the database" is better than "Create a task"
2. **Use natural language** - Write like you're talking to a colleague
3. **Reference existing tasks** - "Update the backup task to run at 3am"
4. **Ask for clarification** - The AI will ask if it needs more information

### 🎯 Task Management Tips

1. **Use descriptive names** - Helps identify tasks later
2. **Test schedules first** - Create tasks as disabled, test manually, then enable
3. **Check execution history** - Monitor task success rates
4. **Use priorities** - Helps organize important vs. routine tasks

### ⚡ Performance Tips

1. **One question at a time** - Wait for responses before sending multiple messages
2. **Refresh if stuck** - If a response seems frozen, refresh the page
3. **Check connection status** - Green indicator means you're connected
4. **Mobile data usage** - WebSocket streaming uses minimal data (~1-2KB per message)

### 🔒 Security Tips

1. **Always use Tailscale** - Never expose port 3000 to the public internet
2. **Log out on shared devices** - Use the logout button in the header
3. **Don't share credentials** - Each user should have their own account
4. **Review task commands** - Verify what tasks will execute before enabling

---

## Troubleshooting

### Connection Issues

#### 🔴 "Connection error" or "Disconnected"

**Possible causes:**
- Backend server is offline
- Tailscale connection dropped
- Network connectivity issue

**Solutions:**
1. Check if backend is running on Mac Mini:
   ```bash
   # On Mac Mini
   lsof -i :8000
   # Should show Python process
   ```
2. Restart backend if needed:
   ```bash
   cd /path/to/ai-assistant-prototype/backend
   python3 main.py
   ```
3. Verify Tailscale is connected:
   ```bash
   tailscale status
   ```
4. Refresh the page - auto-reconnect should kick in

#### 🟡 Stuck on "Connecting..."

**Solutions:**
1. Wait 30 seconds - may be reconnecting
2. Check browser console for errors (F12 → Console tab)
3. Try a hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
4. Clear browser cache if problem persists

### Message Issues

#### Messages not sending

**Symptoms:** Message appears but no AI response

**Solutions:**
1. Check connection status (should be green)
2. Verify backend is responding:
   ```bash
   curl http://[mac-mini-hostname]:8000/health
   # Should return: {"status":"healthy"...}
   ```
3. Check backend logs for errors
4. Refresh the page and try again

#### Messages appear twice

**Cause:** Network hiccup during send

**Solution:**
- Usually resolves on its own
- Refresh page to see accurate message history

#### Old messages not loading

**Solutions:**
1. Refresh the page
2. Check if you're logged in as the correct user
3. Verify database is accessible:
   ```bash
   # On Mac Mini
   sqlite3 ai-assistant.db "SELECT COUNT(*) FROM ChatMessage;"
   ```

### Task Management Issues

#### "Task not found" error

**Cause:** Task was deleted or doesn't exist

**Solution:**
- Ask AI to "show me all tasks" to see what exists
- Use exact task names when referencing tasks

#### Invalid cron schedule error

**Cause:** Cron format is incorrect

**Examples of valid formats:**
- `0 9 * * *` - Every day at 9:00 AM
- `0 0 * * 0` - Every Sunday at midnight
- `*/15 * * * *` - Every 15 minutes
- `0 9 * * 1-5` - Weekdays at 9:00 AM

**Solution:**
- Ask AI to help format the schedule
- Use a cron expression validator online

### Mobile-Specific Issues

#### Keyboard covering input

**Solution:**
- Scroll down to bring input into view
- Use landscape mode for more screen space

#### Text too small

**Solution:**
- Use browser zoom (pinch to zoom)
- Increase text size in device settings

#### Slow responses on mobile data

**Cause:** Weak cellular signal

**Solution:**
- Switch to Wi-Fi if available
- Move to area with better signal
- Responses will still arrive, just slower

---

## Advanced Features

### Keyboard Shortcuts

- **Enter** - Send message
- **Shift+Enter** - New line in message
- **Cmd/Ctrl+R** - Refresh page
- **Cmd/Ctrl+K** - Focus message input (if supported)

### WebSocket Streaming Details

- **Chunk size:** 1KB per update
- **Latency:** <50ms typical
- **Heartbeat:** Every 30 seconds
- **Auto-reconnect:** Up to 5 attempts with exponential backoff
- **Timeout:** 60 seconds without response = disconnect

### Message Limits

- **Content length:** Up to 50,000 characters per message
- **Attachments:** Up to 10 per message (infrastructure present, UI coming soon)
- **History:** Last 50 messages loaded by default

---

## Getting Help

### In-App Support

Ask the AI directly:
```
"How do I create a task?"
"What can you help me with?"
"Explain task scheduling"
```

### System Status

Check the Activity page to see:
- Recent task executions
- System health
- Error logs

### Backend Logs

On Mac Mini, view real-time logs:
```bash
tail -f backend/logs/*.log
```

### Report Issues

If you encounter bugs:
1. Note the exact error message
2. Check what you were doing when it occurred
3. Create a GitHub issue with reproduction steps

---

## Frequently Asked Questions

### Can I use this without Tailscale?

No. The app is designed for private, secure access via Tailscale VPN only. Exposing it to the public internet is not supported or recommended.

### Can multiple people chat at the same time?

Yes! Each user has their own chat history. Multiple users can be connected simultaneously without interfering with each other.

### Are my conversations private?

Yes. Conversations are stored in your local database and are only accessible to your user account. They are transmitted over Tailscale's encrypted VPN.

### How long is chat history kept?

Indefinitely by default. You can clear your chat history using the "Clear conversation" option (future feature) or by asking the AI.

### Can the AI execute arbitrary commands?

No. The AI only has access to task management via the REST API. It can create/modify/delete scheduled tasks, but it cannot execute arbitrary system commands directly. The AI uses Claude Code's Bash tool with curl to interact with the backend API.

### What happens if I lose internet while chatting?

- Your message is saved locally (optimistic update)
- The UI shows "Disconnected" status
- Auto-reconnect attempts start immediately
- Once reconnected, you can continue chatting
- Failed messages may need to be resent

### Can I edit or delete messages?

Not currently. This is a planned feature. For now, you can clear the entire conversation or start a new chat session.

### How do I know if the AI received my message?

- The message appears in the chat immediately (optimistic update)
- "AI is streaming..." indicator appears
- AI response begins streaming within a few seconds
- If no response after 30 seconds, check connection status

---

## Quick Reference Card

### Common Commands

| Action | Example |
|--------|---------|
| Create task | "Create a task to backup database at 2am daily" |
| List tasks | "Show me all my tasks" |
| Update task | "Change the backup task to run at 3am" |
| Delete task | "Delete the test task" |
| View history | "Show execution history for backup task" |
| Run now | "Run the backup task now" |
| Ask for help | "How do I create a task?" |

### Cron Schedule Examples

| Pattern | Description |
|---------|-------------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 0 * * 0` | Every Sunday at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 0 1 * *` | First day of every month |
| `0 14 * * 6` | Saturdays at 2:00 PM |

### Connection Status

| Indicator | Meaning | Action |
|-----------|---------|--------|
| 🟢 Connected | Ready to chat | ✓ Good to go |
| 🟡 Connecting | Establishing connection | ⏳ Wait 10-20 seconds |
| 🔴 Error | Connection failed | 🔄 Check backend/Tailscale |
| ⚪ Disconnected | Not connected | 🔄 Will auto-retry |

---

## Version Information

**Last Updated:** February 12, 2026
**Feature Version:** Phase 2 Complete
**Document Version:** 1.1

**Implemented Features:**
- ✅ Real-time WebSocket streaming
- ✅ Task management via REST API
- ✅ Markdown rendering with syntax highlighting
- ✅ Message persistence and history
- ✅ Auto-reconnection with exponential backoff
- ✅ Mobile responsive design
- ✅ Claude subscription-based execution (no API costs)

**Coming Soon:**
- 🔜 File attachments
- 🔜 Message editing/deletion
- 🔜 Rich message types (task cards, terminal output)
- 🔜 Conversation export
- 🔜 Message search

---

## Feedback & Contributions

This is a personal AI assistant system in active development. If you have suggestions for improving this guide or the chat feature, please create a GitHub issue or submit a pull request.

**Happy chatting! 🤖💬**
