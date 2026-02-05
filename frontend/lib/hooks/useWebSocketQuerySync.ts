import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from './useWebSocket';
import { useTerminalStore } from '../stores/terminalStore';
import { taskKeys } from './useTasks';
import { executionKeys } from './useTaskExecutions';
import { activityLogKeys } from './useActivityLogs';
import type { WebSocketMessage } from '@/lib/websocket';

/**
 * Hook that synchronizes WebSocket messages with React Query cache.
 * Automatically invalidates queries when relevant events occur.
 */
export function useWebSocketQuerySync() {
  const queryClient = useQueryClient();
  const { addLine, setCurrentExecutionId } = useTerminalStore();
  const { subscribe, isConnected } = useWebSocket({ autoConnect: true });

  useEffect(() => {
    if (!isConnected) {
      return;
    }

    // Subscribe to all WebSocket messages
    const unsubscribe = subscribe('*', (message: WebSocketMessage) => {
      const { type, data } = message;

      switch (type) {
        case 'terminal_output': {
          // Add to terminal store
          if (data && typeof data === 'object' && 'content' in data && 'executionId' in data) {
            addLine(String(data.content), 'stdout');
            setCurrentExecutionId(String(data.executionId));
          }
          break;
        }

        case 'status_update': {
          // Invalidate execution queries when status changes
          if (data && typeof data === 'object' && 'executionId' in data) {
            queryClient.invalidateQueries({
              queryKey: executionKeys.detail(String(data.executionId)),
            });
          }
          break;
        }

        case 'execution_start': {
          // Invalidate task and execution queries
          if (data && typeof data === 'object') {
            if ('executionId' in data) {
              setCurrentExecutionId(String(data.executionId));
              addLine(`Execution started: ${data.executionId}`, 'system');
            }

            if ('taskId' in data) {
              queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
              queryClient.invalidateQueries({
                queryKey: executionKeys.list(String(data.taskId)),
              });
            }
          }
          break;
        }

        case 'execution_complete': {
          // Invalidate all related queries
          if (data && typeof data === 'object') {
            if ('executionId' in data && 'status' in data && 'duration' in data) {
              addLine(
                `Execution completed: ${data.status} (${data.duration}ms)`,
                'system'
              );

              queryClient.invalidateQueries({ queryKey: taskKeys.all });
              queryClient.invalidateQueries({
                queryKey: executionKeys.detail(String(data.executionId)),
              });
              queryClient.invalidateQueries({ queryKey: activityLogKeys.all });
            }
          }
          break;
        }

        case 'task_updated':
        case 'task_created':
        case 'task_deleted': {
          // Invalidate task queries
          queryClient.invalidateQueries({ queryKey: taskKeys.all });
          break;
        }

        case 'error': {
          // Add error to terminal
          addLine(`Error: ${JSON.stringify(data)}`, 'stderr');
          break;
        }

        default:
          console.debug('Unhandled WebSocket message type:', type);
      }
    });

    return unsubscribe;
  }, [isConnected, subscribe, queryClient, addLine, setCurrentExecutionId]);

  return { isConnected };
}
