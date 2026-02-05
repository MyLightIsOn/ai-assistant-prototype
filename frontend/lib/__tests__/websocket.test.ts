import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketClient } from '../websocket';

// Mock WebSocket
class MockWebSocket {
  url: string;
  readyState = WebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 10);
  }

  send() {
    // Mock send - intentionally empty for testing
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
}

// Replace global WebSocket with mock
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).WebSocket = MockWebSocket;

describe('WebSocketClient', () => {
  let client: WebSocketClient;

  beforeEach(() => {
    client = new WebSocketClient({
      url: 'ws://localhost:8000/ws',
      autoReconnect: false,
    });
  });

  afterEach(() => {
    client.disconnect();
  });

  it('should create client with disconnected state', () => {
    expect(client.getState()).toBe('disconnected');
    expect(client.isConnected()).toBe(false);
  });

  it('should connect to WebSocket server', async () => {
    client.connect();
    expect(client.getState()).toBe('connecting');

    // Wait for connection to open
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(client.getState()).toBe('connected');
    expect(client.isConnected()).toBe(true);
  });

  it('should disconnect from WebSocket server', async () => {
    client.connect();
    await new Promise(resolve => setTimeout(resolve, 50));

    client.disconnect();
    expect(client.getState()).toBe('disconnected');
    expect(client.isConnected()).toBe(false);
  });

  it('should handle message subscriptions', async () => {
    const handler = vi.fn();

    client.subscribe('terminal_output', handler);
    client.connect();

    await new Promise(resolve => setTimeout(resolve, 50));

    // Simulate incoming message
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const ws = (client as any).ws;
    const message = {
      type: 'terminal_output',
      data: { output: 'test output' },
      timestamp: new Date().toISOString(),
    };

    ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(message) }));

    expect(handler).toHaveBeenCalledWith(message);
  });

  it('should handle wildcard subscriptions', async () => {
    const handler = vi.fn();

    client.subscribe('*', handler);
    client.connect();

    await new Promise(resolve => setTimeout(resolve, 50));

    // Simulate incoming messages
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const ws = (client as any).ws;
    const message1 = {
      type: 'terminal_output',
      data: { output: 'test' },
      timestamp: new Date().toISOString(),
    };
    const message2 = {
      type: 'task_status',
      data: { status: 'running' },
      timestamp: new Date().toISOString(),
    };

    ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(message1) }));
    ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(message2) }));

    expect(handler).toHaveBeenCalledTimes(2);
  });

  it('should unsubscribe from messages', async () => {
    const handler = vi.fn();

    const unsubscribe = client.subscribe('terminal_output', handler);
    client.connect();

    await new Promise(resolve => setTimeout(resolve, 50));

    // Unsubscribe
    unsubscribe();

    // Simulate incoming message
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const ws = (client as any).ws;
    const message = {
      type: 'terminal_output',
      data: { output: 'test' },
      timestamp: new Date().toISOString(),
    };

    ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(message) }));

    expect(handler).not.toHaveBeenCalled();
  });
});
