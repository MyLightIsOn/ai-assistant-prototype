/**
 * Custom React hooks for the AI Assistant application.
 */

// WebSocket hooks
export { useWebSocket } from './useWebSocket';
export { useWebSocketQuerySync } from './useWebSocketQuerySync';

// Task hooks
export {
  useTasks,
  useTask,
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useToggleTask,
  taskKeys,
} from './useTasks';

// Task execution hooks
export {
  useTaskExecutions,
  useExecution,
  useInvalidateExecutions,
  executionKeys,
} from './useTaskExecutions';

// Activity log hooks
export {
  useActivityLogs,
  useExecutionLogs,
  useInvalidateActivityLogs,
  activityLogKeys,
} from './useActivityLogs';
