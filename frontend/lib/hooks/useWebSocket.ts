/**
 * Custom React hook for WebSocket connection management.
 *
 * Features:
 * - Automatic connection/disconnection lifecycle
 * - Connection state management
 * - Message subscription
 * - Session-based authentication
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useSession } from 'next-auth/react';
import {
  WebSocketClient,
  createWebSocketClient,
  ConnectionState,
  WebSocketMessageType,
  MessageHandler,
} from '@/lib/websocket';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  onMessage?: MessageHandler;
}

interface UseWebSocketReturn {
  // Connection state
  state: ConnectionState;
  isConnected: boolean;

  // Actions
  connect: () => void;
  disconnect: () => void;
  send: (type: string, data?: unknown) => void;
  ping: () => void;

  // Subscription
  subscribe: (type: WebSocketMessageType | '*', handler: MessageHandler) => () => void;
}

/**
 * Hook to manage WebSocket connection with authentication.
 *
 * @param options - Configuration options
 * @returns WebSocket connection state and methods
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = true, onMessage } = options;
  const { data: session } = useSession();
  const [state, setState] = useState<ConnectionState>('disconnected');
  const clientRef = useRef<WebSocketClient | null>(null);
  const sessionTokenRef = useRef<string | null>(null);

  // Initialize WebSocket client when session is available
  useEffect(() => {
    // Don't create client if no session
    if (!session?.user) {
      return;
    }

    // Extract session token from session
    // In NextAuth v5 with JWT strategy, we can use the session directly
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sessionToken = (session as any)?.accessToken || 'session-active';
    sessionTokenRef.current = sessionToken;

    // Create WebSocket client
    const client = createWebSocketClient(sessionToken);

    // Update state when connection state changes
    client.subscribe('*', () => {
      setState(client.getState());
    });

    clientRef.current = client;

    // Auto-connect if enabled
    if (autoConnect) {
      client.connect();
    }

    // Cleanup on unmount
    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [session, autoConnect]);

  // Subscribe to all messages if onMessage provided
  useEffect(() => {
    if (!clientRef.current || !onMessage) {
      return;
    }

    const unsubscribe = clientRef.current.subscribe('*', onMessage);
    return unsubscribe;
  }, [onMessage]);

  // Update state when client state changes
  useEffect(() => {
    if (!clientRef.current) {
      return;
    }

    // Poll the state to keep it synchronized
    const interval = setInterval(() => {
      if (clientRef.current) {
        const currentState = clientRef.current.getState();
        if (currentState !== state) {
          setState(currentState);
        }
      }
    }, 500);

    return () => {
      clearInterval(interval);
    };
  }, [state]);

  const connect = useCallback(() => {
    clientRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
  }, []);

  const send = useCallback((type: string, data?: unknown) => {
    clientRef.current?.send(type, data);
  }, []);

  const ping = useCallback(() => {
    clientRef.current?.ping();
  }, []);

  const subscribe = useCallback((type: WebSocketMessageType | '*', handler: MessageHandler) => {
    if (!clientRef.current) {
      // Return no-op unsubscribe function
      return () => {};
    }
    return clientRef.current.subscribe(type, handler);
  }, []);

  const isConnected = state === 'connected';

  return {
    state,
    isConnected,
    connect,
    disconnect,
    send,
    ping,
    subscribe,
  };
}
