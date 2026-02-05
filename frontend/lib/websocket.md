# WebSocket Integration

Real-time WebSocket communication between the frontend and Python backend.

## Architecture

```
Frontend (Next.js)          Backend (FastAPI)
    |                            |
    |---- WebSocket connection ---|
    |    ws://localhost:8000/ws  |
    |                            |
    |<---- terminal_output ------|
    |<---- task_status ----------|
    |<---- notification ---------|
    |<---- activity_log ---------|
    |                            |
    |----- ping --------------->|
    |<---- pong -----------------|
```

## Components

### 1. WebSocket Client (`lib/websocket.ts`)

Low-level WebSocket client with:
- Automatic reconnection with exponential backoff
- Message subscription system
- Connection state management
- Type-safe message handling

**Usage:**
```typescript
import { createWebSocketClient } from '@/lib/websocket';

const client = createWebSocketClient('session-token');

// Connect
client.connect();

// Subscribe to messages
const unsubscribe = client.subscribe('terminal_output', (message) => {
  console.log('Terminal output:', message.data);
});

// Send message
client.send('ping');

// Disconnect
client.disconnect();
```

### 2. WebSocket Hook (`lib/hooks/useWebSocket.ts`)

React hook for WebSocket integration with:
- Session-based authentication
- Automatic connection/disconnection lifecycle
- Message subscription
- Connection state

**Usage:**
```typescript
import { useWebSocket } from '@/lib/hooks/useWebSocket';

function MyComponent() {
  const { state, isConnected, subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('terminal_output', (message) => {
      console.log('Received:', message.data);
    });
    return unsubscribe;
  }, [subscribe]);

  return <div>Status: {state}</div>;
}
```

### 3. Terminal View Component (`components/terminal/TerminalView.tsx`)

Full-featured terminal display with:
- Real-time terminal output streaming
- Auto-scroll functionality
- Connection status indicator
- Clear and export functionality
- Multiple message type support

**Features:**
- Displays terminal output, task status, and connection messages
- Color-coded output (green for output, red for errors, blue for info)
- Auto-scroll with manual override
- Export terminal history to text file

## Message Types

### From Backend to Frontend

| Type | Description | Data Structure |
|------|-------------|----------------|
| `connected` | Connection established | `{ message: string, client_count: number }` |
| `pong` | Response to ping | `{}` |
| `terminal_output` | Terminal output chunk | `{ output: string, type?: 'output'\|'error'\|'info' }` |
| `task_status` | Task status update | `{ taskId: string, status: string }` |
| `notification` | Push notification | `{ title: string, message: string, priority?: string }` |
| `activity_log` | Activity log entry | `{ level: string, message: string, metadata?: object }` |

### From Frontend to Backend

| Type | Description | Data Structure |
|------|-------------|----------------|
| `ping` | Heartbeat request | `{}` |

## Configuration

### Environment Variables

Add to `.env.local`:
```
NEXT_PUBLIC_WS_URL="ws://localhost:8000/ws"
```

### Reconnection Settings

Default settings in `createWebSocketClient()`:
- Max attempts: 5
- Initial delay: 1 second
- Max delay: 30 seconds
- Backoff strategy: Exponential

## Error Handling

The WebSocket client handles:
- Connection failures
- Network interruptions
- Message parsing errors
- Server disconnects

All errors are logged to console and trigger reconnection attempts.

## Testing

Run WebSocket tests:
```bash
npm test -- websocket
```

Tests cover:
- Connection/disconnection
- Message subscriptions
- Wildcard subscriptions
- Unsubscription
- State management

## Integration Example

Complete example with terminal page:

```typescript
// app/(dashboard)/terminal/page.tsx
import { TerminalView } from "@/components/terminal/TerminalView";

export default function TerminalPage() {
  return (
    <div className="space-y-6">
      <h1>Terminal</h1>
      <TerminalView />
    </div>
  );
}
```

The `TerminalView` component automatically:
1. Connects to WebSocket on mount
2. Subscribes to relevant message types
3. Displays messages in real-time
4. Handles connection state changes
5. Disconnects on unmount

## Authentication

The WebSocket connection uses the NextAuth session token for authentication:
1. `useWebSocket` hook extracts session from NextAuth
2. Session token is passed to `createWebSocketClient`
3. Token is appended as query parameter: `ws://localhost:8000/ws?token=...`
4. Backend validates the token (to be implemented in backend)

## Performance

- Message batching: Backend chunks terminal output (1KB or 500ms timeout)
- Auto-scroll optimization: Only scrolls when user is at bottom
- State polling: 500ms interval for connection state synchronization
- Memory management: Terminal output limited to prevent memory bloat

## Future Enhancements

- [ ] Binary message support for large file transfers
- [ ] Message compression for bandwidth optimization
- [ ] Reconnection progress indicator in UI
- [ ] Backend token validation
- [ ] Multiple WebSocket channels per session
- [ ] Message queuing during disconnection
