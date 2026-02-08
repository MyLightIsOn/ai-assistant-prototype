'use client';

import { useState, useEffect } from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  messageType: 'text' | 'task_card' | 'terminal' | 'error';
  metadata?: any;
  createdAt: number;
  attachments?: any[];
}

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch messages on mount
  useEffect(() => {
    fetchMessages();
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

    // Optimistic update
    const optimisticMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      messageType: 'text',
      createdAt: Date.now()
    };
    setMessages(prev => [...prev, optimisticMessage]);
    setIsLoading(true);

    try {
      // Send message
      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, attachments: [] })
      });

      const { messageId } = await response.json();

      // Update optimistic message with real ID
      setMessages(prev => prev.map(msg =>
        msg.id === optimisticMessage.id
          ? { ...msg, id: messageId }
          : msg
      ));

      // Poll for response (will be replaced with WebSocket)
      pollForResponse();

    } catch (error) {
      console.error('Failed to send message:', error);
      setIsLoading(false);
    }
  }

  async function pollForResponse() {
    // Simple polling - will be replaced with WebSocket
    const interval = setInterval(async () => {
      try {
        const response = await fetch('/api/chat/messages?limit=1');
        const data = await response.json();

        if (data.messages.length > 0) {
          const lastMessage = data.messages[data.messages.length - 1];

          if (lastMessage.role === 'assistant' &&
              !messages.find(m => m.id === lastMessage.id)) {
            setMessages(prev => [...prev, lastMessage]);
            setIsLoading(false);
            clearInterval(interval);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 1000);

    // Stop after 30 seconds
    setTimeout(() => {
      clearInterval(interval);
      setIsLoading(false);
    }, 30000);
  }

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} isLoading={isLoading} />
      <ChatInput onSend={handleSendMessage} disabled={isLoading} />
    </div>
  );
}
