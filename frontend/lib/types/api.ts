// API response types based on Prisma schema

export interface MultiAgentMetadata {
  agents: Array<{
    name: string;
    role: string;
  }>;
  synthesis?: boolean;
}

export interface Task {
  id: string;
  userId: string;
  name: string;
  description: string | null;
  command: string;
  args: string;
  schedule: string;
  enabled: boolean;
  priority: string;
  notifyOn: string;
  metadata?: {
    multi_agent?: MultiAgentMetadata;
    [key: string]: any;
  };
  createdAt: string;
  updatedAt: string;
  lastRun: string | null;
  nextRun: string | null;
}

export interface TaskExecution {
  id: string;
  taskId: string;
  status: string;
  startedAt: string;
  completedAt: string | null;
  output: string | null;
  duration: number | null;
}

export interface ActivityLog {
  id: string;
  executionId: string | null;
  type: string;
  message: string;
  metadata: string | null;
  createdAt: string;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  priority: string;
  tags: string | null;
  sentAt: string;
  delivered: boolean;
  readAt: string | null;
}

export interface AiMemory {
  id: string;
  key: string;
  value: string;
  category: string | null;
  createdAt: string;
  updatedAt: string;
}

// API request types
export interface CreateTaskInput {
  name: string;
  description?: string;
  command: string;
  args?: string;
  schedule: string;
  enabled?: boolean;
  priority?: string;
  notifyOn?: string;
}

export interface UpdateTaskInput {
  name?: string;
  description?: string;
  command?: string;
  args?: string;
  schedule?: string;
  enabled?: boolean;
  priority?: string;
  notifyOn?: string;
}

// WebSocket message types
export interface WebSocketMessage {
  type: 'terminal_output' | 'status_update' | 'execution_start' | 'execution_complete' | 'error';
  data: unknown;
}

export interface TerminalOutputMessage extends WebSocketMessage {
  type: 'terminal_output';
  data: {
    executionId: string;
    content: string;
    timestamp: string;
  };
}

export interface StatusUpdateMessage extends WebSocketMessage {
  type: 'status_update';
  data: {
    executionId: string;
    status: string;
    timestamp: string;
  };
}

export interface ExecutionStartMessage extends WebSocketMessage {
  type: 'execution_start';
  data: {
    executionId: string;
    taskId: string;
    timestamp: string;
  };
}

export interface ExecutionCompleteMessage extends WebSocketMessage {
  type: 'execution_complete';
  data: {
    executionId: string;
    status: string;
    duration: number;
    timestamp: string;
  };
}
