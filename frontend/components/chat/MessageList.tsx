'use client';

import { useEffect, useRef } from 'react';
import { Message } from './Message';
import type { ChatMessage } from './ChatContainer';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-center p-8">
        <div className="space-y-4">
          <p className="text-muted-foreground">
            No messages yet. Start a conversation!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="animate-pulse">●</div>
          <span>AI is thinking...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
