/**
 * Custom React hook for WebSocket connection management.
 *
 * Features:
 * - Shared singleton connection across all components
 * - Automatic connection/disconnection lifecycle
 * - Connection state management
 * - Message subscription
 * - Session-based authentication
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useSession } from 'next-auth/react';
import {
  getSharedWebSocketClient,
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
 * All components share a single WebSocket connection via singleton.
 *
 * @param options - Configuration options
 * @returns WebSocket connection state and methods
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = true, onMessage } = options;
  const { data: session } = useSession();
  const [state, setState] = useState<ConnectionState>('disconnected');
  const clientRef = useRef<ReturnType<typeof getSharedWebSocketClient> | null>(null);

  // Stable dependency: only re-run when user identity actually changes
  const userId = session?.user?.id;

  // Connect the shared client when session is available
  useEffect(() => {
    if (!userId) {
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sessionToken = (session as any)?.accessToken || 'session-active';

    // Get shared client (creates new one only if token changed)
    const client = getSharedWebSocketClient(sessionToken);
    clientRef.current = client;

    // Sync state from client
    setState(client.getState());

    // Subscribe to state changes
    const unsubscribe = client.subscribe('*', () => {
      setState(client.getState());
    });

    // Auto-connect if not already connected
    if (autoConnect && !client.isConnected()) {
      client.connect();
    }

    return () => {
      unsubscribe();
    };
  }, [userId, autoConnect]); // eslint-disable-line react-hooks/exhaustive-deps

  // Subscribe to all messages if onMessage provided
  useEffect(() => {
    if (!clientRef.current || !onMessage) {
      return;
    }

    const unsubscribe = clientRef.current.subscribe('*', onMessage);
    return unsubscribe;
  }, [onMessage]);

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
