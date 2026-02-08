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
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

  // Fetch messages on mount
  useEffect(() => {
    fetchMessages();
  }, []);

  // Poll for assistant response
  useEffect(() => {
    if (!isWaitingForResponse) return;

    let intervalId: NodeJS.Timeout;
    let timeoutId: NodeJS.Timeout;

    const poll = async () => {
      try {
        const response = await fetch('/api/chat/messages');
        const data = await response.json();

        // Find new assistant messages
        setMessages(prev => {
          const newMessages = data.messages.filter(
            (msg: ChatMessage) =>
              msg.role === 'assistant' &&
              !prev.find(m => m.id === msg.id)
          );

          if (newMessages.length > 0) {
            setIsWaitingForResponse(false);
            clearInterval(intervalId);
            clearTimeout(timeoutId);
            return [...prev, ...newMessages];
          }

          return prev;
        });
      } catch (error) {
        console.error('Polling error:', error);
      }
    };

    intervalId = setInterval(poll, 1000);
    timeoutId = setTimeout(() => {
      clearInterval(intervalId);
      setIsWaitingForResponse(false);
    }, 30000);

    return () => {
      clearInterval(intervalId);
      clearTimeout(timeoutId);
    };
  }, [isWaitingForResponse]);

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
    setIsWaitingForResponse(true);

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
      } else {
        // Remove failed optimistic message
        setMessages(prev => prev.filter(msg => msg.id !== optimisticId));
        setIsWaitingForResponse(false);
        console.error('Failed to send message:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove failed optimistic message
      setMessages(prev => prev.filter(msg => msg.id !== optimisticId));
      setIsWaitingForResponse(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} isLoading={isWaitingForResponse} />
      <ChatInput onSend={handleSendMessage} disabled={isWaitingForResponse} />
    </div>
  );
}
