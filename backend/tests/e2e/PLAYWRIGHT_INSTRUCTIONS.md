# Playwright E2E Testing with MCP

This directory contains end-to-end tests for the AI Assistant chat UI using Playwright via the Model Context Protocol (MCP).

## Overview

Traditional E2E tests require complex test infrastructure (browser drivers, test frameworks, CI setup). With Playwright MCP integration in Claude Code, we can run browser-based tests conversationally by describing what we want to test.

## Prerequisites

1. **Playwright MCP Server** must be configured in Claude Code
2. **Local development server** must be running:
   ```bash
   npm run dev        # Frontend on port 3000
   npm run dev:backend  # Backend on port 8000
   ```

## How to Run Tests

### Method 1: Conversational Testing (Recommended)

Simply ask Claude Code to run the tests:

```
"Run the E2E tests in backend/tests/e2e/test_chat_ui.py using Playwright"
```

Claude will:
1. Read the test file to understand test scenarios
2. Navigate to the chat UI using Playwright MCP tools
3. Execute each test step interactively
4. Report results back to you

### Method 2: Manual Test Execution

For each test in `test_chat_ui.py`, follow the documented steps manually in a browser and verify expected behavior.

## Test Scenarios

### 1. `test_chat_ui_loads`
**Purpose:** Verify basic chat UI rendering

**Steps:**
1. Navigate to http://localhost:3000/chat
2. Verify page title contains "Chat"
3. Verify message input field exists
4. Verify send button exists

**Expected Result:** All elements present, no console errors

### 2. `test_send_simple_message`
**Purpose:** Verify basic message sending and AI response

**Steps:**
1. Navigate to http://localhost:3000/chat
2. Type "Hello, AI!" in message input
3. Click send button
4. Verify user message appears in chat history
5. Wait for AI response (max 30 seconds)
6. Verify AI response appears below user message
7. Verify response is not empty

**Expected Result:** Round-trip message exchange works, AI responds coherently

### 3. `test_create_task_via_chat`
**Purpose:** Verify task creation through chat interface (MCP integration test)

**Steps:**
1. Navigate to http://localhost:3000/chat
2. Type "Create a task called 'E2E Test Task' that runs tomorrow at 3pm"
3. Click send button
4. Verify user message appears
5. Wait for AI response (max 60 seconds)
6. Verify AI response mentions task creation
7. Verify response includes task name "E2E Test Task"
8. Navigate to http://localhost:3000/tasks
9. Verify task appears in task list
10. Verify task name is "E2E Test Task"

**Expected Result:** Task created successfully, visible in task list, AI confirms creation

### 4. `test_chat_error_handling`
**Purpose:** Verify graceful error handling when backend is unavailable

**Steps:**
1. Stop backend server (simulate backend down)
2. Navigate to http://localhost:3000/chat
3. Try to send a message
4. Verify error message is displayed to user
5. Restart backend server
6. Send message again
7. Verify it works correctly

**Expected Result:** Clear error message shown, recovery works after restart

## Example Playwright MCP Usage

Here's how Claude Code would execute these tests using Playwright MCP tools:

```python
# Claude internally uses these MCP tool calls:

# 1. Navigate to page
browser_navigate(url="http://localhost:3000/chat")

# 2. Take snapshot to see page structure
browser_snapshot()

# 3. Type into message input
browser_type(
    element="message input field",
    ref="[ref from snapshot]",
    text="Hello, AI!",
    submit=False
)

# 4. Click send button
browser_click(
    element="send button",
    ref="[ref from snapshot]"
)

# 5. Wait for response to appear
browser_wait_for(text="response from AI", time=30)

# 6. Take screenshot for verification
browser_take_screenshot(filename="chat-test-result.png")

# 7. Navigate to verify task creation
browser_navigate(url="http://localhost:3000/tasks")
browser_snapshot()
```

## Debugging Failed Tests

If a test fails:

1. **Check console output:**
   ```
   "Show browser console messages"
   ```
   Claude will use `browser_console_messages()` to retrieve errors

2. **Check network requests:**
   ```
   "Show network requests made during the test"
   ```
   Claude will use `browser_network_requests()` to see API calls

3. **Take a screenshot:**
   ```
   "Take a screenshot of the current page"
   ```
   Visual verification of UI state

4. **Inspect page state:**
   ```
   "Show the current page snapshot"
   ```
   Get accessibility tree view of page elements

## Best Practices

1. **Always run with fresh state:** Clear browser cache/storage between test runs
2. **Check backend logs:** Verify API calls are being made correctly
3. **Verify WebSocket connection:** Chat requires active WebSocket for streaming
4. **Test with realistic timing:** Don't rush through tests - AI responses take time
5. **Clean up test data:** Delete test tasks after verification

## Troubleshooting

**Problem:** "Playwright not found" error
**Solution:** Ensure Playwright MCP server is configured in `~/.claude/mcp_settings.json`

**Problem:** Page doesn't load
**Solution:** Verify dev servers are running (`npm run dev` and `npm run dev:backend`)

**Problem:** AI doesn't respond in chat
**Solution:** Check WebSocket connection in browser DevTools Network tab

**Problem:** Task creation fails
**Solution:** Verify backend has access to MCP filesystem server for task storage

## Additional Resources

- [Playwright MCP Documentation](https://github.com/anthropics/mcp-playwright)
- [Claude Code MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [AI Assistant Architecture Docs](../../docs/ARCHITECTURE.md)
