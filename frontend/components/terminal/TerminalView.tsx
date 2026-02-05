"use client";

import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Trash2, Download, Terminal as TerminalIcon, Wifi, WifiOff } from 'lucide-react';
import { useWebSocket } from '@/lib/hooks/useWebSocket';
import { WebSocketMessage } from '@/lib/websocket';

interface TerminalLine {
  id: string;
  text: string;
  timestamp: Date;
  type?: 'output' | 'error' | 'info';
}

interface TerminalViewProps {
  className?: string;
}

export function TerminalView({ className }: TerminalViewProps) {
  const [lines, setLines] = useState<TerminalLine[]>([]);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const terminalRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // WebSocket connection
  const { state, isConnected, subscribe } = useWebSocket({
    autoConnect: true,
  });

  // Subscribe to terminal output messages
  useEffect(() => {
    const unsubscribe = subscribe('terminal_output', (message: WebSocketMessage) => {
      const { data } = message;
      // Type guard for terminal output data
      const terminalData = data as { output?: string; text?: string; type?: string };

      const newLine: TerminalLine = {
        id: `${Date.now()}-${Math.random()}`,
        text: terminalData.output || terminalData.text || String(data),
        timestamp: new Date(message.timestamp),
        type: (terminalData.type as 'output' | 'error' | 'info') || 'output',
      };

      setLines(prev => [...prev, newLine]);
    });

    return unsubscribe;
  }, [subscribe]);

  // Subscribe to task status updates
  useEffect(() => {
    const unsubscribe = subscribe('task_status', (message: WebSocketMessage) => {
      const { data } = message;
      // Type guard for task status data
      const taskData = data as { taskId?: string; status?: string };

      const statusLine: TerminalLine = {
        id: `${Date.now()}-${Math.random()}`,
        text: `[Task ${taskData.taskId || 'unknown'}] Status: ${taskData.status}`,
        timestamp: new Date(message.timestamp),
        type: 'info',
      };

      setLines(prev => [...prev, statusLine]);
    });

    return unsubscribe;
  }, [subscribe]);

  // Subscribe to connection status
  useEffect(() => {
    const unsubscribe = subscribe('connected', (message: WebSocketMessage) => {
      // Type guard for connection data
      const connData = message.data as { message?: string };

      const welcomeLine: TerminalLine = {
        id: `${Date.now()}-${Math.random()}`,
        text: connData.message || 'Connected to backend',
        timestamp: new Date(message.timestamp),
        type: 'info',
      };

      setLines(prev => [...prev, welcomeLine]);
    });

    return unsubscribe;
  }, [subscribe]);

  // Auto-scroll to bottom when new lines are added
  useEffect(() => {
    if (isAutoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [lines, isAutoScroll]);

  // Handle scroll to detect manual scrolling
  const handleScroll = useCallback(() => {
    if (!terminalRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = terminalRef.current;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10;

    setIsAutoScroll(isAtBottom);
  }, []);

  // Clear terminal
  const handleClear = useCallback(() => {
    setLines([]);
  }, []);

  // Export terminal output
  const handleExport = useCallback(() => {
    const content = lines
      .map(line => `[${line.timestamp.toISOString()}] ${line.text}`)
      .join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `terminal-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [lines]);

  // Get connection status badge
  const getConnectionBadge = () => {
    switch (state) {
      case 'connected':
        return (
          <Badge variant="default" className="bg-green-500">
            <Wifi className="h-3 w-3 mr-1" />
            Connected
          </Badge>
        );
      case 'connecting':
        return (
          <Badge variant="secondary">
            <Wifi className="h-3 w-3 mr-1 animate-pulse" />
            Connecting...
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="destructive">
            <WifiOff className="h-3 w-3 mr-1" />
            Error
          </Badge>
        );
      default:
        return (
          <Badge variant="outline">
            <WifiOff className="h-3 w-3 mr-1" />
            Disconnected
          </Badge>
        );
    }
  };

  // Get line color based on type
  const getLineColor = (type?: string) => {
    switch (type) {
      case 'error':
        return 'text-red-400';
      case 'info':
        return 'text-blue-400';
      default:
        return 'text-green-400';
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TerminalIcon className="h-5 w-5" />
            <CardTitle>Live Terminal Output</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {getConnectionBadge()}
            <Button
              variant="outline"
              size="sm"
              onClick={handleClear}
              disabled={lines.length === 0}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Clear
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={lines.length === 0}
            >
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
        <CardDescription>
          Streaming output from Claude Code subprocess
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          ref={terminalRef}
          onScroll={handleScroll}
          className="bg-black/95 rounded-lg p-4 h-[500px] overflow-auto font-mono text-sm"
        >
          {lines.length === 0 ? (
            <div className="flex items-center gap-2 text-green-400">
              <TerminalIcon className="h-4 w-4" />
              <span>
                {isConnected
                  ? 'Terminal ready. Waiting for task execution...'
                  : 'Connecting to backend...'}
              </span>
            </div>
          ) : (
            <div className="space-y-1">
              {lines.map(line => (
                <div key={line.id} className={`${getLineColor(line.type)} whitespace-pre-wrap`}>
                  <span className="text-gray-500 text-xs mr-2">
                    {line.timestamp.toLocaleTimeString()}
                  </span>
                  {line.text}
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {!isAutoScroll && (
          <div className="mt-2 text-sm text-muted-foreground text-center">
            Scroll to bottom to enable auto-scroll
          </div>
        )}
      </CardContent>
    </Card>
  );
}
