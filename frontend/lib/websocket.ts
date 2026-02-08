/**
 * WebSocket client utility for real-time communication with backend.
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Connection state management
 * - Type-safe message handling
 * - Authentication via session token
 */

// Message types from backend
export type WebSocketMessageType =
  | 'connected'
  | 'pong'
  | 'ping'
  | 'terminal_output'
  | 'task_status'
  | 'notification'
  | 'activity_log'
  | 'echo'
  | 'status_update'
  | 'execution_start'
  | 'execution_complete'
  | 'task_updated'
  | 'task_created'
  | 'task_deleted'
  | 'agent_started'
  | 'agent_completed'
  | 'agent_failed'
  | 'agent_output'
  | 'chat_stream_start'
  | 'chat_stream'
  | 'chat_stream_complete'
  | 'chat_stream_error'
  | 'error';

export interface WebSocketMessage<T = unknown> {
  type: WebSocketMessageType;
  data: T;
  timestamp: string;
}

// Connection states
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

// Message handlers type
export type MessageHandler = (message: WebSocketMessage) => void;

interface WebSocketClientOptions {
  url: string;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  initialReconnectDelay?: number;
  maxReconnectDelay?: number;
  onStateChange?: (state: ConnectionState) => void;
}

/**
 * WebSocket client with automatic reconnection and message handling.
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private autoReconnect: boolean;
  private maxReconnectAttempts: number;
  private initialReconnectDelay: number;
  private maxReconnectDelay: number;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private state: ConnectionState = 'disconnected';
  private messageHandlers: Map<WebSocketMessageType | '*', Set<MessageHandler>> = new Map();
  private onStateChange?: (state: ConnectionState) => void;
  private intentionallyClosed = false;

  constructor(options: WebSocketClientOptions) {
    this.url = options.url;
    this.autoReconnect = options.autoReconnect ?? true;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 5;
    this.initialReconnectDelay = options.initialReconnectDelay ?? 1000;
    this.maxReconnectDelay = options.maxReconnectDelay ?? 30000;
    this.onStateChange = options.onStateChange;
  }

  /**
   * Connect to WebSocket server.
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.intentionallyClosed = false;
    this.setState('connecting');

    try {
      this.ws = new WebSocket(this.url);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.setState('error');
      this.handleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server.
   */
  disconnect(): void {
    this.intentionallyClosed = true;
    this.clearReconnectTimeout();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.setState('disconnected');
  }

  /**
   * Send message to server.
   */
  send(type: string, data: unknown = {}): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected. Message not sent:', { type, data });
      return;
    }

    const message = {
      type,
      data,
      timestamp: new Date().toISOString(),
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Send ping to server for heartbeat.
   */
  ping(): void {
    this.send('ping');
  }

  /**
   * Subscribe to specific message type or all messages.
   *
   * @param type - Message type to subscribe to, or '*' for all messages
   * @param handler - Callback function to handle the message
   * @returns Unsubscribe function
   */
  subscribe(type: WebSocketMessageType | '*', handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }

    this.messageHandlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.messageHandlers.delete(type);
        }
      }
    };
  }

  /**
   * Get current connection state.
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Check if WebSocket is connected.
   */
  isConnected(): boolean {
    return this.state === 'connected';
  }

  /**
   * Setup WebSocket event handlers.
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.setState('connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.setState('error');
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.setState('disconnected');

      if (!this.intentionallyClosed && this.autoReconnect) {
        this.handleReconnect();
      }
    };
  }

  /**
   * Handle incoming message from server.
   */
  private handleMessage(message: WebSocketMessage): void {
    // Call handlers for specific message type
    const typeHandlers = this.messageHandlers.get(message.type);
    if (typeHandlers) {
      typeHandlers.forEach(handler => handler(message));
    }

    // Call wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach(handler => handler(message));
    }
  }

  /**
   * Handle reconnection with exponential backoff.
   */
  private handleReconnect(): void {
    if (this.intentionallyClosed || this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached or intentionally closed');
      return;
    }

    this.reconnectAttempts++;

    // Calculate delay with exponential backoff
    const delay = Math.min(
      this.initialReconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Clear reconnect timeout.
   */
  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  /**
   * Set connection state and notify listeners.
   */
  private setState(newState: ConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.onStateChange?.call(null, newState);
    }
  }
}

/**
 * Create WebSocket client instance.
 *
 * @param sessionToken - Optional session token for authentication
 * @returns WebSocket client instance
 */
export function createWebSocketClient(sessionToken?: string): WebSocketClient {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

  // Append session token as query parameter if provided
  const url = sessionToken ? `${wsUrl}?token=${encodeURIComponent(sessionToken)}` : wsUrl;

  return new WebSocketClient({
    url,
    autoReconnect: true,
    maxReconnectAttempts: 5,
    initialReconnectDelay: 1000,
    maxReconnectDelay: 30000,
  });
}
