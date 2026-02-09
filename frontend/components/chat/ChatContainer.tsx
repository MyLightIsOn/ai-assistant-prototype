'use client';

import { useState, useEffect } from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  messageType: 'text' | 'task_card' | 'terminal' | 'error';
  metadata?: Record<string, unknown>;
  createdAt: number;
  attachments?: Array<{
    id: string;
    fileName: string;
    filePath: string;
    fileType: string;
    fileSize: number;
  }>;
}

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

  // Fetch messages function
  const fetchMessages = async () => {
    try {
      const response = await fetch('/api/chat/messages');
      const data = await response.json();
      setMessages(data.messages);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  };

  // Fetch messages on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchMessages();
  }, []);

  // Poll for assistant response
  useEffect(() => {
    if (!isWaitingForResponse) return;

    const poll = async () => {
      try {
        const response = await fetch('/api/chat/messages');
        const data = await response.json();

        // Find new assistant messages that have actual content
        // (the backend creates an empty placeholder first, then fills it in)
        const newMessages = (data.messages as ChatMessage[]).filter(
          (msg) =>
            msg.role === 'assistant' &&
            msg.content &&
            msg.content.length > 0
        );

        setMessages(prev => {
          const lastAssistant = newMessages[newMessages.length - 1];
          if (lastAssistant && !prev.find(m => m.id === lastAssistant.id)) {
            setIsWaitingForResponse(false);
            clearInterval(intervalId);
            clearTimeout(timeoutId);
            // Replace full message list from server to stay in sync
            return data.messages.filter(
              (msg: ChatMessage) => !msg.role || msg.content?.length > 0
            );
          }

          return prev;
        });
      } catch (error) {
        console.error('Polling error:', error);
      }
    };

    const intervalId = setInterval(poll, 1000);
    const timeoutId = setTimeout(() => {
      clearInterval(intervalId);
      setIsWaitingForResponse(false);
      // On timeout, refresh from server anyway
      void fetchMessages();
    }, 30000);

    return () => {
      clearInterval(intervalId);
      clearTimeout(timeoutId);
    };
  }, [isWaitingForResponse]);

  async function handleSendMessage(content: string) {
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
