import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { TaskExecution } from '../types/api';

// Query keys
export const executionKeys = {
  all: ['executions'] as const,
  lists: () => [...executionKeys.all, 'list'] as const,
  list: (taskId: string) => [...executionKeys.lists(), taskId] as const,
  details: () => [...executionKeys.all, 'detail'] as const,
  detail: (id: string) => [...executionKeys.details(), id] as const,
};

// Fetch executions for a task
export function useTaskExecutions(taskId: string | null) {
  return useQuery({
    queryKey: executionKeys.list(taskId ?? ''),
    queryFn: async (): Promise<TaskExecution[]> => {
      if (!taskId) throw new Error('Task ID is required');
      const response = await fetch(`/api/tasks/${taskId}/executions`);
      if (!response.ok) {
        throw new Error('Failed to fetch task executions');
      }
      return response.json();
    },
    enabled: !!taskId,
  });
}

// Fetch single execution
export function useExecution(id: string | null) {
  return useQuery({
    queryKey: executionKeys.detail(id ?? ''),
    queryFn: async (): Promise<TaskExecution> => {
      if (!id) throw new Error('Execution ID is required');
      const response = await fetch(`/api/executions/${id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch execution');
      }
      return response.json();
    },
    enabled: !!id,
  });
}

// Hook to invalidate execution queries (called from WebSocket)
export function useInvalidateExecutions() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: executionKeys.all });
    },
    invalidateTask: (taskId: string) => {
      queryClient.invalidateQueries({ queryKey: executionKeys.list(taskId) });
    },
    invalidateExecution: (id: string) => {
      queryClient.invalidateQueries({ queryKey: executionKeys.detail(id) });
    },
  };
}
