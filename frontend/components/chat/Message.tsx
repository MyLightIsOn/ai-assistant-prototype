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
  const isStreaming = message.isStreaming ?? false;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-lg p-4 ${
        isUser
          ? 'bg-primary text-primary-foreground'
          : 'bg-muted'
      }`}>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          {message.content ? (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          ) : isStreaming ? (
            <div className="flex items-center gap-2 text-muted-foreground italic">
              <span className="inline-block w-2 h-2 bg-current rounded-full animate-pulse" />
              <span>Thinking...</span>
            </div>
          ) : null}
        </div>

        {isStreaming && message.content && (
          <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
            <span className="inline-block w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="inline-block w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="inline-block w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        )}

        <div className={`text-xs mt-2 ${
          isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
        }`}>
          {formatDistanceToNow(timestamp, { addSuffix: true })}
        </div>
      </div>
    </div>
  );
}
