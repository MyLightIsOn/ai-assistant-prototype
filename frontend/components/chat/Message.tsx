'use client';

import ReactMarkdown from 'react-markdown';
import { formatDistanceToNow } from 'date-fns';
import type { ChatMessage } from './ChatContainer';

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';
  const timestamp = new Date(message.createdAt);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-lg p-4 ${
        isUser
          ? 'bg-primary text-primary-foreground'
          : 'bg-muted'
      }`}>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        <div className={`text-xs mt-2 ${
          isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
        }`}>
          {formatDistanceToNow(timestamp, { addSuffix: true })}
        </div>
      </div>
    </div>
  );
}
