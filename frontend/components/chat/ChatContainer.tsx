'use client';

import { useState, useEffect, useRef } from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { WebSocketClient, type ConnectionState } from '@/lib/websocket';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  messageType: 'text' | 'task_card' | 'terminal' | 'error';
  metadata?: any;
  createdAt: number;
  attachments?: any[];
  isStreaming?: boolean;
}

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const wsClient = useRef<WebSocketClient | null>(null);

  // Initialize WebSocket connection
  useEffect(() => {
    // Fetch initial messages
    fetchMessages();

    // Create WebSocket client with connection state tracking
    const client = new WebSocketClient({
      url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
      autoReconnect: true,
      maxReconnectAttempts: 5,
      initialReconnectDelay: 1000,
      maxReconnectDelay: 30000,
      onStateChange: (state: ConnectionState) => {
        setConnectionState(state);
      }
    });
    wsClient.current = client;

    // Subscribe to chat streaming events
    const unsubscribeStart = client.subscribe('chat_stream_start', (message) => {
      const { message_id } = message.data as { message_id: string };

      // Create placeholder assistant message
      setMessages(prev => [...prev, {
        id: message_id,
        role: 'assistant',
        content: '',
        messageType: 'text',
        createdAt: Date.now(),
        isStreaming: true
      }]);
      setIsWaitingForResponse(true);
    });

    const unsubscribeStream = client.subscribe('chat_stream', (message) => {
      const { message_id, chunk } = message.data as { message_id: string; chunk: string };

      // Append chunk to assistant message
      setMessages(prev => prev.map(msg =>
        msg.id === message_id
          ? { ...msg, content: msg.content + chunk }
          : msg
      ));
    });

    const unsubscribeComplete = client.subscribe('chat_stream_complete', (message) => {
      const { message_id, final_content } = message.data as { message_id: string; final_content: string };

      // Update final content and remove streaming flag
      setMessages(prev => prev.map(msg =>
        msg.id === message_id
          ? { ...msg, content: final_content, isStreaming: false }
          : msg
      ));
      setIsWaitingForResponse(false);
    });

    const unsubscribeError = client.subscribe('chat_stream_error', (message) => {
      const { message_id, error } = message.data as { message_id: string; error: string };

      // Update message with error
      setMessages(prev => prev.map(msg =>
        msg.id === message_id
          ? { ...msg, content: `Error: ${error}`, messageType: 'error', isStreaming: false }
          : msg
      ));
      setIsWaitingForResponse(false);
    });

    // Connect to WebSocket
    client.connect();

    // Cleanup on unmount
    return () => {
      unsubscribeStart();
      unsubscribeStream();
      unsubscribeComplete();
      unsubscribeError();
      client.disconnect();
    };
  }, []);

  async function fetchMessages() {
    try {
      const response = await fetch('/api/chat/messages');
      const data = await response.json();
      setMessages(data.messages);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  }

  async function handleSendMessage(content: string, attachments: File[]) {
    // TODO: Handle file uploads

    // Optimistic update with guaranteed unique ID
    const optimisticId = crypto.randomUUID();
    const optimisticMessage: ChatMessage = {
      id: optimisticId,
      role: 'user',
      content,
      messageType: 'text',
      createdAt: Date.now()
    };
    setMessages(prev => [...prev, optimisticMessage]);

    try {
      // Send message
      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, attachments: [] })
      });

      if (response.ok) {
        const { messageId } = await response.json();

        // Replace optimistic message with real ID
        setMessages(prev => prev.map(msg =>
          msg.id === optimisticId
            ? { ...msg, id: messageId }
            : msg
        ));

        // Streaming will start via WebSocket chat_stream_start event
      } else {
        // Remove failed optimistic message
        setMessages(prev => prev.filter(msg => msg.id !== optimisticId));
        console.error('Failed to send message:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove failed optimistic message
      setMessages(prev => prev.filter(msg => msg.id !== optimisticId));
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Connection status badge */}
      <div className="border-b bg-white px-4 py-2">
        <div className="flex items-center gap-2 text-sm">
          <div className={`h-2 w-2 rounded-full ${
            connectionState === 'connected' ? 'bg-green-500' :
            connectionState === 'connecting' ? 'bg-yellow-500 animate-pulse' :
            connectionState === 'error' ? 'bg-red-500' :
            'bg-gray-400'
          }`} />
          <span className="text-gray-600">
            {connectionState === 'connected' ? 'Connected' :
             connectionState === 'connecting' ? 'Connecting...' :
             connectionState === 'error' ? 'Connection error' :
             'Disconnected'}
          </span>
          {isWaitingForResponse && (
            <span className="ml-auto text-gray-500 italic">AI is streaming...</span>
          )}
        </div>
      </div>

      <MessageList messages={messages} isLoading={isWaitingForResponse} />
      <ChatInput onSend={handleSendMessage} disabled={isWaitingForResponse} />
    </div>
  );
}
